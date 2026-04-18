/*
 * Machine.cpp
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#include "Machine.h"
#include <cstring>
#include <algorithm>
#include <cstdio>
#include <cmath>
using std::min;
using std::max;

#define DEBUG_STATES

Machine::Machine(ICoreXY& icorexy,
				 IStepper& istepper_z,
                 ITMC2209& itmc_a, ITMC2209& itmc_b, ITMC2209& itmc_z,
				 IGPIO& igpio_endstop_x,
				 IGPIO& igpio_endstop_y,
				 IGPIO& igpio_endstop_z,
				 IServo& iservo,
				 IUART& iuart)
    : icorexy_(icorexy),
      istepper_z_(istepper_z),
      itmc_a_(itmc_a),
      itmc_b_(itmc_b),
      itmc_z_(itmc_z),
	  igpio_endstop_x_(igpio_endstop_x),
	  igpio_endstop_y_(igpio_endstop_y),
	  igpio_endstop_z_(igpio_endstop_z),
	  iservo_(iservo),
	  iuart_(iuart) {}

void Machine::init()
{
	char tx_msg[32];
	if (!(itmc_a_.isConnected() && itmc_b_.isConnected() && itmc_z_.isConnected())) {
		snprintf(tx_msg, 32, "TMC Connection Error\n");
		iuart_.UART_Transmit((uint8_t*)tx_msg, 32);
	}

	itmc_a_.init(TMC2209_CFG_XY);
	itmc_b_.init(TMC2209_CFG_XY);
	itmc_z_.init(TMC2209_CFG_Z);

    // Enable all axes
    icorexy_.enable();
    istepper_z_.enable();

    // init and enable the servo output
	iservo_.init();

    setState(MachineState::UNHOMED);
    sendState();
}

void Machine::update()
{
    switch (state_) {

    	case MachineState::HOMING_X_INITIAL_STEPBACK:
    		if (!icorexy_.isMoving()) { startHomingXFast(); }
    		break;

    	case MachineState::HOMING_X_STEPBACK:
            if (!icorexy_.isMoving()) { startHomingXSlow(); }
            break;

    	case MachineState::HOMING_Y_INITIAL_STEPBACK:
    		if (!icorexy_.isMoving()) { startHomingYFast(); }
    		break;

        case MachineState::HOMING_Y_STEPBACK:
            if (!icorexy_.isMoving()) { startHomingYSlow(); }
            break;

        case MachineState::HOMING_Z_INITIAL_STEPBACK:
            if (!istepper_z_.isMoving()) { startHomingZFast(); }
            break;

        case MachineState::HOMING_Z_STEPBACK:
            if (!istepper_z_.isMoving()) { startHomingZSlow(); }
            break;

        case MachineState::MOVING:
            if (!icorexy_.isMoving() && !istepper_z_.isMoving()) {
                setState(MachineState::IDLE);
				//sendState();
				sendOk();
            }
            break;

        default:
            break;
    }
}

void Machine::setState(MachineState new_state) { state_ = new_state; }

void Machine::sendState()
{
	const char* name = "UNKNOWN\n";
	switch(state_) {
		case MachineState::UNHOMED: name = "UNHOMED\n"; break;
		case MachineState::HOMING_X_INITIAL_STEPBACK: name = "HOMING_X_INITIAL_STEPBACK\n"; break;
		case MachineState::HOMING_X_FAST: name = "HOMING_X_FAST\n"; break;
		case MachineState::HOMING_X_STEPBACK: name = "HOMING_X_STEPBACK\n"; break;
		case MachineState::HOMING_X_SLOW: name = "HOMING_X_SLOW\n"; break;
		case MachineState::HOMING_Y_INITIAL_STEPBACK: name = "HOMING_Y_INITIAL_STEPBACK\n"; break;
		case MachineState::HOMING_Y_FAST: name = "HOMING_Y_FAST\n"; break;
		case MachineState::HOMING_Y_STEPBACK: name = "HOMING_Y_STEPBACK\n"; break;
		case MachineState::HOMING_Y_SLOW: name = "HOMING_Y_SLOW\n"; break;
		case MachineState::HOMING_Z_INITIAL_STEPBACK: name = "HOMING_Z_INITIAL_STEPBACK\n"; break;
		case MachineState::HOMING_Z_FAST: name = "HOMING_Z_FAST\n"; break;
		case MachineState::HOMING_Z_STEPBACK: name = "HOMING_Z_STEPBACK\n"; break;
		case MachineState::HOMING_Z_SLOW: name = "HOMING_Z_SLOW\n"; break;
		case MachineState::HOMED: name = "HOMED\n"; break;
		case MachineState::IDLE: name = "IDLE\n"; break;
		case MachineState::MOVING: name = "MOVING\n"; break;
		case MachineState::STOPPING: name = "STOPPING\n"; break;
		case MachineState::FAULT: name = "FAULT\n"; break;
		default: break;
	}
	iuart_.UART_Transmit((uint8_t*)name, strlen(name));
}

void Machine::sendOk()
{
    const char* msg = "ok\n";
    iuart_.UART_Transmit((uint8_t*)msg, strlen(msg));
    //HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), 100);
}

void Machine::sendBusy()
{
    const char* msg = "busy\n";
    iuart_.UART_Transmit((uint8_t*)msg, strlen(msg));
    //HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), 100);
}

void Machine::sendError(const char* msg) { iuart_.UART_Transmit((uint8_t*)msg, strlen(msg)); }

void Machine::handleCommand(const ParsedCommand& cmd)
{
	if (cmd.error) { sendError("error: unknown command\n"); return; }

	if (strcmp(cmd.cmd, "G28") == 0) { handleG28(cmd); return; }
    if (strcmp(cmd.cmd, "G0")  == 0) { handleG0(cmd);  return; }
    if (strcmp(cmd.cmd, "M400") == 0) { handleM400(cmd); return; }
    if (strcmp(cmd.cmd, "STOP") == 0) { handleStop(cmd); return; }
    if (strcmp(cmd.cmd, "M114") == 0) { handleM114(cmd); return; }
    if (strcmp(cmd.cmd, "M119") == 0) { handleM119(cmd); return; }
    if (strcmp(cmd.cmd, "M280") == 0) { handleM280(cmd); return; }

    sendError("error: unknown command\n");
}

void Machine::handleG0(const ParsedCommand& cmd)
{
	// Clamp to bed bounds
	float target_x = max(0.0f, min(BED_SIZE_MM, cmd.x));
	float target_y = max(0.0f, min(BED_SIZE_MM, cmd.y));
	float target_z = max(0.0f, min(Z_MAX_MM, cmd.z));   // adjust Z max to your bed travel

	if (state_ == MachineState::MOVING) { sendBusy(); return; }
    if (state_ == MachineState::UNHOMED) { sendError("error: not homed\n"); return; }

    float feedrate = cmd.has_f ? cmd.f : 1000.0f;

    if (cmd.has_x || cmd.has_y) {
        float dx = cmd.has_x ? target_x - icorexy_.getX() : 0.0f;
        float dy = cmd.has_y ? target_y - icorexy_.getY() : 0.0f;
        icorexy_.move(dx, dy, feedrate, ACCEL_XY_MM_S2);
    }

    if (cmd.has_z) {
        float dz = target_z - istepper_z_.getPosition();
        istepper_z_.move(dz, feedrate, ACCEL_Z_MM_S2);
    }

    setState(MachineState::MOVING);
    // Don't send ok yet -- send when move completes in update()
}

void Machine::handleM400(const ParsedCommand& cmd)
{
    // Block until move complete -- main loop handles this
    // For now just report current state
    if (!icorexy_.isMoving() && !istepper_z_.isMoving()) {
        sendOk();
    }
    // else -- ok sent when move completes in update()
}

void Machine::handleStop(const ParsedCommand& cmd)
{
    icorexy_.stop();
    istepper_z_.stop();
    setState(MachineState::IDLE);
    sendOk();
}

void Machine::handleG28(const ParsedCommand& cmd)
{
    if (state_ == MachineState::MOVING) { sendBusy(); return; }
    startHomingX();
}

void Machine::handleM114(const ParsedCommand& cmd)
{
    float x = icorexy_.getX();
    float y = icorexy_.getY();
    float z = istepper_z_.getPosition();

    char buf[64];
    snprintf(buf, sizeof(buf), "X:%d.%02d Y:%d.%02d Z:%d.%02d\n",
             (int)x, (int)(fabsf(fmodf(x, 1.0f)) * 100),
             (int)y, (int)(fabsf(fmodf(y, 1.0f)) * 100),
             (int)z, (int)(fabsf(fmodf(z, 1.0f)) * 100));

    iuart_.UART_Transmit((uint8_t*)buf, strlen(buf));
}

void Machine::handleM119(const ParsedCommand& cmd)
{
    bool endstop_x = igpio_endstop_x_.readPin();
    bool endstop_y = igpio_endstop_y_.readPin();
    bool endstop_z = igpio_endstop_z_.readPin();

    char buf[64];
    snprintf(buf, sizeof(buf), "X endstop:%d Y endstop:%d Z endstop:%d\n",
    		(int)endstop_x,
			(int)endstop_y,
			(int)endstop_z);

    iuart_.UART_Transmit((uint8_t*)buf, strlen(buf));
}

void Machine::handleM280(const ParsedCommand& cmd)
{
    if (cmd.has_s) {
        iservo_.setAngle(cmd.s);
    }
    sendOk();
}

void Machine::startHomingX()
{
    setState(MachineState::HOMING_X_INITIAL_STEPBACK);
    icorexy_.move(-HOMING_STEPBACK_XY, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    //sendState();
}

void Machine::startHomingXFast()
{
    setState(MachineState::HOMING_X_FAST);
    icorexy_.move(HOMING_DISTANCE_XY, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    //sendState();
}

void Machine::startHomingXStepback()
{
    setState(MachineState::HOMING_X_STEPBACK);
    icorexy_.move(-HOMING_STEPBACK_XY, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    //sendState();
}

void Machine::startHomingXSlow()
{
    setState(MachineState::HOMING_X_SLOW);
    icorexy_.move(HOMING_DISTANCE_XY, 0.0f, HOMING_FEEDRATE_SLOW_XY, HOMING_ACCEL_XY);
    //sendState();
}

// ── Y homing ─────────────────────────────────────────────────────────────────

void Machine::startHomingY()
{
    setState(MachineState::HOMING_Y_INITIAL_STEPBACK);
    icorexy_.move(0.0f, -HOMING_STEPBACK_XY, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    //sendState();
}

void Machine::startHomingYFast()
{
    setState(MachineState::HOMING_Y_FAST);
    icorexy_.move(0.0f, HOMING_DISTANCE_XY, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    //sendState();
}

void Machine::startHomingYStepback()
{
    setState(MachineState::HOMING_Y_STEPBACK);
    icorexy_.move(0.0f, -HOMING_STEPBACK_XY, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    //sendState();
}

void Machine::startHomingYSlow()
{
    setState(MachineState::HOMING_Y_SLOW);
    icorexy_.move(0.0f, HOMING_DISTANCE_XY, HOMING_FEEDRATE_SLOW_XY, HOMING_ACCEL_XY);
    //sendState();
}

// ── Z homing ─────────────────────────────────────────────────────────────────

void Machine::startHomingZ()
{
    setState(MachineState::HOMING_Z_INITIAL_STEPBACK);
    istepper_z_.move(HOMING_STEPBACK_Z, HOMING_FEEDRATE_FAST_Z, ACCEL_Z_MM_S2);
    //sendState();
}

void Machine::startHomingZFast()
{
    setState(MachineState::HOMING_Z_FAST);
    istepper_z_.move(-HOMING_DISTANCE_Z, HOMING_FEEDRATE_FAST_Z, ACCEL_Z_MM_S2);
    //sendState();
}
void Machine::startHomingZStepback()
{
    setState(MachineState::HOMING_Z_STEPBACK);
    istepper_z_.move(HOMING_STEPBACK_Z, HOMING_FEEDRATE_FAST_Z, ACCEL_Z_MM_S2);
    //sendState();
}

void Machine::startHomingZSlow()
{
    setState(MachineState::HOMING_Z_SLOW);
    istepper_z_.move(-HOMING_DISTANCE_Z, HOMING_FEEDRATE_SLOW_Z, HOMING_ACCEL_Z);
    //sendState();
}

void Machine::onXYStall()
{
    switch (state_) {
        case MachineState::HOMING_X_FAST:
            icorexy_.stop();
            startHomingXStepback();
            break;
        case MachineState::HOMING_X_SLOW:
            icorexy_.stop();
            icorexy_.setPosition(120.0f, icorexy_.getY());
            startHomingY();
            break;
        case MachineState::HOMING_Y_FAST:
            icorexy_.stop();
            startHomingYStepback();
            break;
        case MachineState::HOMING_Y_SLOW:
            icorexy_.stop();
            icorexy_.setPosition(icorexy_.getX(), 120.0f);
            startHomingZ();
            break;
        default:
            break;
    }
}

void Machine::onZEndstop()
{
    switch (state_) {
        case MachineState::HOMING_Z_FAST:
            istepper_z_.stop();
            startHomingZStepback();
            break;
        case MachineState::HOMING_Z_SLOW:
            istepper_z_.stop();
            istepper_z_.setPosition(0.0f);
            setState(MachineState::HOMED);
            sendOk();
            break;
        default:
            break;
    }
}

Machine::~Machine() = default;

