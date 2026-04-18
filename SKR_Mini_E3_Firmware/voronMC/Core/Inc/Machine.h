/*
 * Machine.h
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#ifndef SRC_MACHINE_H_
#define SRC_MACHINE_H_

#pragma once
#include "CommandParser.h"
#include "Config.h"
#include "IClass/ICoreXY.h"
#include "IClass/IStepper.h"
#include "IClass/ITMC2209.h"
#include "IClass/IServo.h"
#include "IHAL/IUART.h"
#include "IHAL/IGPIO.h"

enum class MachineState {
    UNHOMED,
    HOMING_X_INITIAL_STEPBACK,   // added
    HOMING_X_FAST,
    HOMING_X_STEPBACK,
    HOMING_X_SLOW,
    HOMING_Y_INITIAL_STEPBACK,   // added
    HOMING_Y_FAST,
    HOMING_Y_STEPBACK,
    HOMING_Y_SLOW,
    HOMING_Z_INITIAL_STEPBACK,   // added
    HOMING_Z_FAST,
    HOMING_Z_STEPBACK,
    HOMING_Z_SLOW,
    HOMED,
    IDLE,
    MOVING,
    STOPPING,
    FAULT,
};

class Machine {
public:
    Machine(ICoreXY& icorexy,
            IStepper& istepper_z,
            ITMC2209& itmc_a,
            ITMC2209& itmc_b,
            ITMC2209& itmc_z,
			IGPIO& igpio_endstop_x,
			IGPIO& igpio_endstop_y,
			IGPIO& igpio_endstop_z,
			IServo& iservo,
			IUART& iuart);

    void init();
    void update();  // called from main loop

    // Command dispatch -- called from main loop when command_ready
    void handleCommand(const ParsedCommand& cmd);

    // Endstop/StallGuard callbacks -- called from GPIO EXTI ISR
    void onXYStall(void);
    void onZEndstop(void);

    // State queries -- used by ISR to decide whether to act
    bool isHomingX() const {
        return state_ == MachineState::HOMING_X_FAST ||
               state_ == MachineState::HOMING_X_SLOW;
    }
    bool isHomingY() const {
        return state_ == MachineState::HOMING_Y_FAST ||
               state_ == MachineState::HOMING_Y_SLOW;
    }
    bool isHomingZ() const {
        return state_ == MachineState::HOMING_Z_FAST ||
               state_ == MachineState::HOMING_Z_SLOW;
    }
    bool isMoving(void)  const { return state_ == MachineState::MOVING; }

    MachineState getState() const { return state_; }

    // State transitions
    void setState(MachineState new_state);
    void sendState();

    void startHomingX();
    void startHomingXFast();
    void startHomingXStepback();
    void startHomingXSlow();
    void startHomingY();
    void startHomingYFast();
    void startHomingYStepback();
    void startHomingYSlow();
    void startHomingZ();
    void startHomingZFast();
    void startHomingZStepback();
    void startHomingZSlow();

    virtual ~Machine(void);

private:
    ICoreXY&  icorexy_;
    IStepper& istepper_z_;
    ITMC2209& itmc_a_;
    ITMC2209& itmc_b_;
    ITMC2209& itmc_z_;
    IGPIO&    igpio_endstop_x_;
    IGPIO&    igpio_endstop_y_;
    IGPIO&    igpio_endstop_z_;
    IServo&   iservo_;
    IUART&    iuart_;

    MachineState state_ = MachineState::UNHOMED;

    // Response helpers
    void sendOk();
    void sendBusy();
    void sendError(const char* msg);


    // G-code handlers
    void handleG28(const ParsedCommand& cmd);
    void handleG0(const ParsedCommand& cmd);
    void handleM400(const ParsedCommand& cmd);
    void handleStop(const ParsedCommand& cmd);
    void handleM114(const ParsedCommand& cmd);
    void handleM119(const ParsedCommand& cmd);
    void handleM280(const ParsedCommand& cmd);
};

#endif /* SRC_MACHINE_H_ */
