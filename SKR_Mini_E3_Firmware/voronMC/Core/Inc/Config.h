/*
 * config.h
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#ifndef INC_CONFIG_H_
#define INC_CONFIG_H_

#include "IClass/ITMC2209.h"
#include <cstdint>

static constexpr TMC2209Config TMC2209_CFG_XY = {
		.run_current      = 7,
		.hold_current     = 3,
		.microsteps       = 32,
		.sg_threshold     = 30,
		.ihold_delay      = 3,
		.tpowerdown       = 20,
		.tcool_threshold  = 0xFFFFF,
		.en_spreadcycle   = false,
		.pdn_disable      = true,
		.mstep_reg_select = true,
		.sg_enable		  = true};

static constexpr TMC2209Config TMC2209_CFG_Z = {
		.run_current      = 14,
		.hold_current     = 7,
		.microsteps       = 32,
		.sg_threshold     = 30,
		.ihold_delay      = 3,
		.tpowerdown       = 20,
		.tcool_threshold  = 0xFFFFF,
		.en_spreadcycle   = false,
		.pdn_disable      = true,
		.mstep_reg_select = true,
		.sg_enable		  = true};

// ── Motion Configuration ──────────────────────────────────────────────────────
static constexpr float STEPS_PER_MM_XY      = 160.0f;
static constexpr float STEPS_PER_MM_Z       = 800.0f;
static constexpr float BED_SIZE_MM          = 120.0f;
static constexpr float Z_MAX_MM             = 120.0f;

// ── Homing Configuration ──────────────────────────────────────────────────────
static constexpr float HOMING_FEEDRATE_FAST_XY   = 3000.0f;  // mm/min
static constexpr float HOMING_FEEDRATE_SLOW_XY   = 1000.0f;   // mm/min
static constexpr float HOMING_FEEDRATE_FAST_Z    = 1000.0f;   // mm/min
static constexpr float HOMING_FEEDRATE_SLOW_Z    = 200.0f;   // mm/min
static constexpr float HOMING_DISTANCE_XY        = 125.0f;   // mm max travel
static constexpr float HOMING_STEPBACK_XY		 = 5.0f;	 // mm
static constexpr float HOMING_DISTANCE_Z         = 125.0f;   // mm max travel
static constexpr float HOMING_STEPBACK_Z         = 2.0f;     // mm
static constexpr float HOMING_ACCEL_XY			 = 10000.0f; //mm/s²
static constexpr float HOMING_ACCEL_Z			 = 100.0f;   //mm/s²

// ── Communication ─────────────────────────────────────────────────────────────
static constexpr uint32_t PI_UART_BAUD         = 115200;
static constexpr uint32_t TMC_UART_BAUD        = 115200;

static constexpr uint16_t SERVO_MIN_PULSE_US  = 100;
static constexpr uint16_t SERVO_MAX_PULSE_US  = 2000;

static constexpr float ACCEL_XY_MM_S2   = 1000.0f;   // mm/s²
static constexpr float ACCEL_Z_MM_S2    = 300.0f;   // mm/s²
static constexpr float MIN_SPEED_MM_MIN = 50.0f;     // mm/min -- starting speed

// ── STM32 HAL constants────────────────────────────────────────────────────────
static constexpr uint32_t TIMER_CLOCK_HZ = 1000000UL;

#endif /* INC_CONFIG_H_ */
