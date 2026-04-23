#include <gtest/gtest.h>
#include "MockCoreXY.h"
#include "MockStepper.h"
#include "MockTMC2209Simple.h"
#include "MockServo.h"
#include "MockUART.h"
#include "MockGPIO.h"
#include "Machine.h"
#include "CommandParser.h"
#include "Config.h"
#include <cstring>

// ── helpers ───────────────────────────────────────────────────────────────────

static ParsedCommand makeCommand(const char* cmd,
                                  bool has_x = false, float x = 0.0f,
                                  bool has_y = false, float y = 0.0f,
                                  bool has_z = false, float z = 0.0f,
                                  bool has_f = false, float f = 0.0f,
                                  bool has_s = false, float s = 0.0f)
{
    ParsedCommand c{};
    strncpy(c.cmd, cmd, sizeof(c.cmd));
    c.has_x = has_x; c.x = x;
    c.has_y = has_y; c.y = y;
    c.has_z = has_z; c.z = z;
    c.has_f = has_f; c.f = f;
    c.has_s = has_s; c.s = s;
    return c;
}

// ── fixture ───────────────────────────────────────────────────────────────────

class MachineTest : public ::testing::Test {
protected:
    MockCoreXY      mockcorexy;
    MockStepper     mockstepper_z;
    MockTMC2209Simple mocktmc_a, mocktmc_b, mocktmc_z;
    MockGPIO        mockgpio_endstop_x;
    MockGPIO        mockgpio_endstop_y;
    MockGPIO        mockgpio_endstop_z;
    MockServo       mockservo;
    MockUART        mockuart;
    Machine         machine;

    MachineTest()
        : machine(mockcorexy, mockstepper_z,
                  mocktmc_a, mocktmc_b, mocktmc_z,
				  mockgpio_endstop_x,
				  mockgpio_endstop_y,
				  mockgpio_endstop_z,
                  mockservo, mockuart)
    {}

    // helper -- put machine in IDLE state ready for move commands
    void setIdle() {
        machine.setState(MachineState::IDLE);
    }

    // helper -- put machine in HOMED state
    void setHomed() {
        machine.setState(MachineState::HOMED);
    }

    // helper -- put machine in MOVING state with both axes moving
    void setMoving() {
        machine.setState(MachineState::MOVING);
        mockcorexy.moving = true;
        mockstepper_z.stepsRemaining = 1;
    }
};

// ── init ──────────────────────────────────────────────────────────────────────

TEST_F(MachineTest, InitSetsUnhomedState)
{
    machine.init();
    EXPECT_EQ(machine.getState(), MachineState::UNHOMED);
}

TEST_F(MachineTest, InitEnablesAxes)
{
    machine.init();
    EXPECT_TRUE(mockcorexy.enabled);
}

TEST_F(MachineTest, InitCallsTMCInit)
{
    machine.init();
    EXPECT_TRUE(mocktmc_a.init_called);
    EXPECT_TRUE(mocktmc_b.init_called);
    EXPECT_TRUE(mocktmc_z.init_called);
}

TEST_F(MachineTest, InitInitialisesServo)
{
    machine.init();
    EXPECT_TRUE(mockservo.PWM_run);
}

// ── state queries ─────────────────────────────────────────────────────────────

TEST_F(MachineTest, IsHomingXTrueWhenHomingXFast)
{
    machine.setState(MachineState::HOMING_X_FAST);
    EXPECT_TRUE(machine.isHomingX());
}

TEST_F(MachineTest, IsHomingXTrueWhenHomingXSlow)
{
    machine.setState(MachineState::HOMING_X_SLOW);
    EXPECT_TRUE(machine.isHomingX());
}

TEST_F(MachineTest, IsHomingXFalseWhenIdle)
{
    setIdle();
    EXPECT_FALSE(machine.isHomingX());
}

TEST_F(MachineTest, IsHomingYTrueWhenHomingYFast)
{
    machine.setState(MachineState::HOMING_Y_FAST);
    EXPECT_TRUE(machine.isHomingY());
}

TEST_F(MachineTest, IsHomingYTrueWhenHomingYSlow)
{
    machine.setState(MachineState::HOMING_Y_SLOW);
    EXPECT_TRUE(machine.isHomingY());
}

TEST_F(MachineTest, IsHomingZTrueWhenHomingZFast)
{
    machine.setState(MachineState::HOMING_Z_FAST);
    EXPECT_TRUE(machine.isHomingZ());
}

TEST_F(MachineTest, IsHomingZTrueWhenHomingZSlow)
{
    machine.setState(MachineState::HOMING_Z_SLOW);
    EXPECT_TRUE(machine.isHomingZ());
}

TEST_F(MachineTest, IsMovingTrueWhenMoving)
{
    machine.setState(MachineState::MOVING);
    EXPECT_TRUE(machine.isMoving());
}

TEST_F(MachineTest, IsMovingFalseWhenIdle)
{
    setIdle();
    EXPECT_FALSE(machine.isMoving());
}

// ── handleG28 ─────────────────────────────────────────────────────────────────

TEST_F(MachineTest, G28RejectedWhenMoving)
{
    setMoving();
    machine.handleCommand(makeCommand("G28"));
    EXPECT_EQ(machine.getState(), MachineState::MOVING);

    // verify busy response sent
    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "busy\n");
}

TEST_F(MachineTest, G28StartsHomingX)
{
    setIdle();
    machine.handleCommand(makeCommand("G28"));
    EXPECT_EQ(machine.getState(), MachineState::HOMING_X_INITIAL_STEPBACK);
}

TEST_F(MachineTest, G28MovesCorexyCoreXY)
{
    setIdle();
    machine.handleCommand(makeCommand("G28"));
    EXPECT_TRUE(mockcorexy.move_called);
}

// ── handleG0 ──────────────────────────────────────────────────────────────────

TEST_F(MachineTest, G0RejectedWhenMoving)
{
    setMoving();
    machine.handleCommand(makeCommand("G0", true, 10.0f));
    EXPECT_EQ(machine.getState(), MachineState::MOVING);

    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "busy\n");
}

TEST_F(MachineTest, G0RejectedWhenUnhomed)
{
    machine.setState(MachineState::UNHOMED);
    machine.handleCommand(makeCommand("G0", true, 10.0f));

    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "error: not homed\n");
}

TEST_F(MachineTest, G0SetsMovingState)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", true, 10.0f, true, 10.0f));
    EXPECT_EQ(machine.getState(), MachineState::MOVING);
}

TEST_F(MachineTest, G0ClampsXToBedMin)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", true, -10.0f));
    EXPECT_FLOAT_EQ(mockcorexy.last_dx, 0.0f);
}

TEST_F(MachineTest, G0ClampsXToBedMax)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", true, BED_SIZE_MM + 10.0f));
    EXPECT_FLOAT_EQ(mockcorexy.last_dx, BED_SIZE_MM);
}

TEST_F(MachineTest, G0ClampsYToBedMin)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", false, 0.0f, true, -10.0f));
    EXPECT_FLOAT_EQ(mockcorexy.last_dy, 0.0f);
}

TEST_F(MachineTest, G0ClampsYToBedMax)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", false, 0.0f, true, BED_SIZE_MM + 10.0f));
    EXPECT_FLOAT_EQ(mockcorexy.last_dy, BED_SIZE_MM);
}

TEST_F(MachineTest, G0UsesDefaultFeedrateWhenNoF)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", true, 10.0f));
    EXPECT_FLOAT_EQ(mockcorexy.last_feedrate, 1000.0f);
}

TEST_F(MachineTest, G0UsesFeedrateWhenProvided)
{
    setIdle();
    machine.handleCommand(makeCommand("G0", true, 10.0f,
                                      false, 0.0f,
                                      false, 0.0f,
                                      true, 3000.0f));
    EXPECT_FLOAT_EQ(mockcorexy.last_feedrate, 3000.0f);
}

// ── update ────────────────────────────────────────────────────────────────────

TEST_F(MachineTest, UpdateTransitionsMovingToIdleWhenBothStopped)
{
    setMoving();
    mockcorexy.moving = false;
    mockstepper_z.stepsRemaining = 0;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::IDLE);
}

TEST_F(MachineTest, UpdateSendsOkWhenMoveComplete)
{
    setMoving();
    mockcorexy.moving = false;
    mockstepper_z.stepsRemaining = 0;
    machine.update();

    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "ok\n");
}

TEST_F(MachineTest, UpdateStaysMovingWhenCoreXYStillMoving)
{
    setMoving();
    mockcorexy.moving = true;
    mockstepper_z.stepsRemaining = 0;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::MOVING);
}

TEST_F(MachineTest, UpdateStaysMovingWhenZStillMoving)
{
    setMoving();
    mockcorexy.moving = false;
    mockstepper_z.stepsRemaining = 1;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::MOVING);
}

TEST_F(MachineTest, UpdateTransitionsFromInitialStepbackXWhenNotMoving)
{
    machine.setState(MachineState::HOMING_X_INITIAL_STEPBACK);
    mockcorexy.moving = false;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_X_FAST);
}

TEST_F(MachineTest, UpdateStaysInInitialStepbackXWhenMoving)
{
    machine.setState(MachineState::HOMING_X_INITIAL_STEPBACK);
    mockcorexy.moving = true;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_X_INITIAL_STEPBACK);
}

TEST_F(MachineTest, UpdateTransitionsFromStepbackXWhenNotMoving)
{
    machine.setState(MachineState::HOMING_X_STEPBACK);
    mockcorexy.moving = false;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_X_SLOW);
}

TEST_F(MachineTest, UpdateTransitionsFromInitialStepbackYWhenNotMoving)
{
    machine.setState(MachineState::HOMING_Y_INITIAL_STEPBACK);
    mockcorexy.moving = false;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Y_FAST);
}

TEST_F(MachineTest, UpdateTransitionsFromStepbackYWhenNotMoving)
{
    machine.setState(MachineState::HOMING_Y_STEPBACK);
    mockcorexy.moving = false;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Y_SLOW);
}

TEST_F(MachineTest, UpdateTransitionsFromInitialStepbackZWhenNotMoving)
{
    machine.setState(MachineState::HOMING_Z_INITIAL_STEPBACK);
    mockstepper_z.stepsRemaining = 0;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Z_FAST);
}

TEST_F(MachineTest, UpdateTransitionsFromStepbackZWhenNotMoving)
{
    machine.setState(MachineState::HOMING_Z_STEPBACK);
    mockstepper_z.stepsRemaining = 0;
    machine.update();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Z_SLOW);
}

// ── onXYStall ─────────────────────────────────────────────────────────────────

TEST_F(MachineTest, OnXYStallDuringHomingXFastStartsStepback)
{
    machine.setState(MachineState::HOMING_X_FAST);
    machine.onXYStall();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_X_STEPBACK);
}

TEST_F(MachineTest, OnXYStallDuringHomingXSlowSetsPositionAndStartsY)
{
    machine.setState(MachineState::HOMING_X_SLOW);
    machine.onXYStall();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Y_INITIAL_STEPBACK);
    EXPECT_FLOAT_EQ(mockcorexy.x, 120.0f);
}

TEST_F(MachineTest, OnXYStallDuringHomingYFastStartsStepback)
{
    machine.setState(MachineState::HOMING_Y_FAST);
    machine.onXYStall();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Y_STEPBACK);
}

TEST_F(MachineTest, OnXYStallDuringHomingYSlowSetsPositionAndStartsZ)
{
    machine.setState(MachineState::HOMING_Y_SLOW);
    machine.onXYStall();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Z_INITIAL_STEPBACK);
    EXPECT_FLOAT_EQ(mockcorexy.y, 120.0f);
}

TEST_F(MachineTest, OnXYStallIgnoredWhenNotHoming)
{
    setIdle();
    machine.onXYStall();
    EXPECT_EQ(machine.getState(), MachineState::IDLE);
}

// ── onZEndstop ────────────────────────────────────────────────────────────────

TEST_F(MachineTest, OnZEndstopDuringHomingZFastStartsStepback)
{
    machine.setState(MachineState::HOMING_Z_FAST);
    machine.onZEndstop();
    EXPECT_EQ(machine.getState(), MachineState::HOMING_Z_STEPBACK);
}

TEST_F(MachineTest, OnZEndstopDuringHomingZSlowSetsHomedState)
{
    machine.setState(MachineState::HOMING_Z_SLOW);
    machine.onZEndstop();
    EXPECT_EQ(machine.getState(), MachineState::HOMED);
}

TEST_F(MachineTest, OnZEndstopDuringHomingZSlowSetsZPositionZero)
{
    machine.setState(MachineState::HOMING_Z_SLOW);
    machine.onZEndstop();
    EXPECT_FLOAT_EQ(mockstepper_z.position, 0.0f);
}

TEST_F(MachineTest, OnZEndstopDuringHomingZSlowSendsOk)
{
    machine.setState(MachineState::HOMING_Z_SLOW);
    machine.onZEndstop();
    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "ok\n");
}

TEST_F(MachineTest, OnZEndstopIgnoredWhenNotHoming)
{
    setIdle();
    machine.onZEndstop();
    EXPECT_EQ(machine.getState(), MachineState::IDLE);
}

// ── handleStop ────────────────────────────────────────────────────────────────

TEST_F(MachineTest, StopStopsCoreXY)
{
    setMoving();
    machine.handleCommand(makeCommand("STOP"));
    EXPECT_FALSE(mockcorexy.moving);
}

TEST_F(MachineTest, StopStopsZ)
{
    setMoving();
    machine.handleCommand(makeCommand("STOP"));
    EXPECT_EQ(mockstepper_z.stepsRemaining, 0);
}

TEST_F(MachineTest, StopSendsOk)
{
    machine.handleCommand(makeCommand("STOP"));
    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "ok\n");
}

// ── handleM280 ────────────────────────────────────────────────────────────────

TEST_F(MachineTest, M280SetsServoAngle)
{
    machine.handleCommand(makeCommand("M280", false, 0.0f,
                                      false, 0.0f,
                                      false, 0.0f,
                                      false, 0.0f,
                                      true, 90.0f));
    EXPECT_FLOAT_EQ(mockservo.last_angle, 90.0f);
}

TEST_F(MachineTest, M280SendsOk)
{
    machine.handleCommand(makeCommand("M280", false, 0.0f,
                                      false, 0.0f,
                                      false, 0.0f,
                                      false, 0.0f,
                                      true, 90.0f));
    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "ok\n");
}

// ── handleM400 ────────────────────────────────────────────────────────────────

TEST_F(MachineTest, M400SendsOkWhenNotMoving)
{
    setIdle();
    machine.handleCommand(makeCommand("M400"));
    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "ok\n");
}

TEST_F(MachineTest, M400NoResponseWhenMoving)
{
    setMoving();
    machine.handleCommand(makeCommand("M400"));
    EXPECT_TRUE(mockuart.last_tx_message.empty());
}

// ── unknown command ───────────────────────────────────────────────────────────

TEST_F(MachineTest, UnknownCommandSendsError)
{
    machine.handleCommand(makeCommand("G99"));
    std::string response(mockuart.last_tx_message.begin(),
                         mockuart.last_tx_message.end());
    EXPECT_EQ(response, "error: unknown command\n");
}

//tmc.isConnected error state
