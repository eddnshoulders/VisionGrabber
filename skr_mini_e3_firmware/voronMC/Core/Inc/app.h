/*
 * app.h
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#ifndef INC_APP_H_
#define INC_APP_H_

#pragma once
#include "main.h"

typedef void(*task_fcn_t)(void);

typedef struct {
	task_fcn_t fcn;
	uint32_t period_ms;
	uint32_t next_run;
} periodic_task_t;

void run_task_1ms(void);
void run_task_10ms(void);
void run_task_100ms(void);
void run_task_1s(void);
void app_init(void);
void app_while(void);
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart);

#endif /* INC_APP_H_ */
