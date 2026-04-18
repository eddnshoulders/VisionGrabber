/*
 * app.cpp
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#include "HALImp/UARTImp.h"
#include "HALImp/TimerImp.h"
#include "HALImp/GPIOImp.h"
#include "HALImp/SYSImp.h"
#include "app.h"
#include "CommandParser.h"
#include "TMC2209.h"
#include "Stepper.h"
#include "CoreXY.h"
#include "Machine.h"
#include "Config.h"
#include "Servo.h"
#include <cstdio>
#include <cmath>

extern "C" {
#include "app_isr.h"
}

CommandParser parser;
extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim5;
extern TIM_HandleTypeDef htim8;
extern UART_HandleTypeDef huart2;
extern UART_HandleTypeDef huart4;
uint8_t rx_byte;
volatile bool command_parsed;
volatile bool tmc_test;

volatile uint32_t tim1_isr_count = 0;
volatile uint32_t tim2_isr_count = 0;
volatile uint32_t tim8_isr_count = 0;


// ****************************************
// MOVE THESE TO MACHINE CLASS ONCE CREATED
UARTImp uartimptmc(&huart4);
TMC2209 tmc_a(uartimptmc, 0);
TMC2209 tmc_b(uartimptmc, 2);
TMC2209 tmc_z(uartimptmc, 1);
// ****************************************

SYSImp sysimp;

TimerImp timerimp_stepper_a(&htim1);
GPIOImp igpioimp_en_stepper_a(AEN_GPIO_Port,   AEN_Pin);
GPIOImp igpioimp_dir_stepper_a(ADIR_GPIO_Port,  ADIR_Pin);
GPIOImp igpioimp_step_stepper_a(ASTEP_GPIO_Port, ASTEP_Pin);

Stepper stepper_a(timerimp_stepper_a,
		igpioimp_en_stepper_a,
		igpioimp_dir_stepper_a,
		igpioimp_step_stepper_a,
		sysimp,
		STEPS_PER_MM_XY,
        false);

TimerImp timerimp_stepper_b(&htim2);
GPIOImp igpioimp_en_stepper_b(BEN_GPIO_Port,   BEN_Pin);
GPIOImp igpioimp_dir_stepper_b(BDIR_GPIO_Port,  BDIR_Pin);
GPIOImp igpioimp_step_stepper_b(BSTEP_GPIO_Port, BSTEP_Pin);

Stepper stepper_b(timerimp_stepper_b,
		igpioimp_en_stepper_b,
		igpioimp_dir_stepper_b,
		igpioimp_step_stepper_b,
		sysimp,
		STEPS_PER_MM_XY,
		false);

TimerImp timerimp_stepper_z(&htim8);
GPIOImp igpioimp_en_stepper_z(ZEN_GPIO_Port,   ZEN_Pin);
GPIOImp igpioimp_dir_stepper_z(ZDIR_GPIO_Port,  ZDIR_Pin);
GPIOImp igpioimp_step_stepper_z(ZSTEP_GPIO_Port, ZSTEP_Pin);

Stepper stepper_z(timerimp_stepper_z,
		igpioimp_en_stepper_z,
		igpioimp_dir_stepper_z,
		igpioimp_step_stepper_z,
		sysimp,
		STEPS_PER_MM_Z,
        true);

// CoreXY instance -- composed of A and B steppers
CoreXY corexy(stepper_a, stepper_b, STEPS_PER_MM_XY);

TimerImp timerimp(&htim5, TIM_CHANNEL_2);
Servo servo(timerimp, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);

GPIOImp igpioimp_endstop_x(XSTOP_GPIO_Port,   XSTOP_Pin);
GPIOImp igpioimp_endstop_y(YSTOP_GPIO_Port,   YSTOP_Pin);
GPIOImp igpioimp_endstop_z(ZSTOP_GPIO_Port,   ZSTOP_Pin);
UARTImp uartimpcmd(&huart2);
Machine machine(corexy,
				stepper_z,
				tmc_a, tmc_b, tmc_z,
				igpioimp_endstop_x,
				igpioimp_endstop_y,
				igpioimp_endstop_z,
				servo,
				uartimpcmd);

extern "C" void app_on_xy_stall()    { machine.onXYStall(); }
extern "C" void app_on_z_endstop()  { machine.onZEndstop(); }

void app_user2() {
	HAL_GPIO_WritePin(GPIOB,AEN_Pin|BEN_Pin|ZEN_Pin, GPIO_PIN_SET);	// disable all stepper driver outputs
	HAL_UART_Receive_IT(&huart2, &rx_byte, 1); // enable RX interrupt on command UART
	machine.init();
}

void app_user_while() {
	if (command_parsed) {
		command_parsed = false;
		machine.handleCommand(parser.getCommand());
	}
	machine.update();

}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART2) {
    	// Complete command ready -- handle in main loop via flag
        if (parser.processByte(rx_byte)) { command_parsed = true; }
        HAL_UART_Receive_IT(&huart2, &rx_byte, 1);
    }
}

extern "C" void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {
    if ((GPIO_Pin == XSTOP_Pin) || (GPIO_Pin == YSTOP_Pin)) app_on_xy_stall();
     else if (GPIO_Pin == ZSTOP_Pin) app_on_z_endstop();
}

void app_tim1_update() {
	tim1_isr_count++;
	stepper_a.onTimer();
}
void app_tim2_update() {
	tim2_isr_count++;
	stepper_b.onTimer();
}
void app_tim8_update() {
	tim8_isr_count++;
	stepper_z.onTimer();
}
