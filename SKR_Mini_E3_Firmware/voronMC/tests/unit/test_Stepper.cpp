#include <gtest/gtest.h>
#include "MockTimer.h"
#include "MockGPIO.h"
#include "MockSYS.h"
#include "Stepper.h"
#include "Config.h"
#include <cmath>
#include <iostream>

// helper to calc number of accel/decel steps
int32_t calcAccelSteps(float target_speed_mm_min, float accel_mm_s2) {
    float min_speed_steps_s = (MIN_SPEED_MM_MIN / 60.0f) * STEPS_PER_MM_XY;
    float target_speed_steps_s = (target_speed_mm_min / 60.0f) * STEPS_PER_MM_XY;
    float accel_steps_s2 = accel_mm_s2 * STEPS_PER_MM_XY;
    return (target_speed_steps_s * target_speed_steps_s - min_speed_steps_s * min_speed_steps_s) / (2.0f * accel_steps_s2);
}

// test fixture class
class StepperTest : public ::testing::Test {
protected:
    MockTimer mocktimer;
    MockGPIO mockgpio_en;
    MockGPIO mockgpio_dir;
    MockGPIO mockgpio_step;
    MockSYS mocksys;
    Stepper stepper;

    StepperTest()
	: stepper(mocktimer, mockgpio_en, mockgpio_dir, mockgpio_step, mocksys, STEPS_PER_MM_XY, false)
    {}
};

TEST_F(StepperTest, Enable) {
    stepper.enable();
    EXPECT_TRUE(stepper.checkEnabled());
    EXPECT_FALSE(mockgpio_en.pinSt);
}

TEST_F(StepperTest, Disable) {
    stepper.disable();
    EXPECT_TRUE(mockgpio_en.pinSt);
}

TEST_F(StepperTest, Stop) {
    stepper.stop();
    EXPECT_FALSE(mocktimer.IT_run);
    EXPECT_EQ(stepper.getStepsRemaining(), 0);
    EXPECT_FLOAT_EQ(stepper.getCurrentSpeedStepsS(), 0.0f);
}

TEST_F(StepperTest, InvertDir) {
    stepper.move(20.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_TRUE(mockgpio_dir.pinSt);
    stepper.setInvertDir(true);
    stepper.move(20.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_FALSE(mockgpio_dir.pinSt);
}

TEST_F(StepperTest, StepsPerMMSet) {
    EXPECT_FLOAT_EQ(stepper.getStepsPerMm(), STEPS_PER_MM_XY);
}

TEST_F(StepperTest, MoveCalc0mm) {
    // checking early return when steps = 0 but making sure all vars are at default values
    stepper.move(0.0, 3000.0f, 1000.0f);
    EXPECT_TRUE(stepper.getDirection());
    EXPECT_FALSE(mockgpio_dir.pinSt);
    EXPECT_EQ(stepper.getStepsRemaining(), 0);

    EXPECT_NEAR(stepper.getCurrentSpeedStepsS(), 0.0f, 0.01f);
    EXPECT_FLOAT_EQ(stepper.getTargetSpeedStepsS(), 0.0f);
    EXPECT_FLOAT_EQ(stepper.getAccelStepsS2(), 0.0f);

    EXPECT_FALSE(mocktimer.IT_run);
    EXPECT_EQ(mocktimer.period_reg, 0);
    EXPECT_EQ(mocktimer.counter_reg, 0);
}

TEST_F(StepperTest, MoveCalc20mmFwd) {
    // checking early return when steps = 0 but making sure all vars are at default values
    float mm = 20.0f;
    stepper.move(mm, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_TRUE(stepper.getDirection());
    EXPECT_TRUE(mockgpio_dir.pinSt);
    EXPECT_EQ(stepper.getStepsRemaining(), STEPS_PER_MM_XY * std::abs(mm));

    float currentSpeedSteps = (MIN_SPEED_MM_MIN / 60.0f) * STEPS_PER_MM_XY;
    EXPECT_NEAR(stepper.getCurrentSpeedStepsS(), currentSpeedSteps, 0.01f);
    EXPECT_FLOAT_EQ(stepper.getTargetSpeedStepsS(), (HOMING_FEEDRATE_FAST_XY / 60) * STEPS_PER_MM_XY);
    EXPECT_FLOAT_EQ(stepper.getAccelStepsS2(), ACCEL_XY_MM_S2 * STEPS_PER_MM_XY);
    EXPECT_NEAR(stepper.getMinSpeedStepsS(), (MIN_SPEED_MM_MIN / 60.0f) * STEPS_PER_MM_XY, 0.01f);

    EXPECT_TRUE(mocktimer.IT_run);
    EXPECT_NEAR(mocktimer.period_reg, TIMER_CLOCK_HZ / currentSpeedSteps, 0.1f);
    EXPECT_EQ(mocktimer.counter_reg, 0);
}

TEST_F(StepperTest, MoveCalc20mmRev) {
    // checking early return when steps = 0 but making sure all vars are at default values
    float mm = -20.0f;
    stepper.move(mm, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_FALSE(stepper.getDirection());
    EXPECT_FALSE(mockgpio_dir.pinSt);
    EXPECT_EQ(stepper.getStepsRemaining(), STEPS_PER_MM_XY * std::abs(mm));

    float currentSpeedStepsS = (MIN_SPEED_MM_MIN / 60.0f) * STEPS_PER_MM_XY;
    EXPECT_NEAR(stepper.getCurrentSpeedStepsS(), currentSpeedStepsS, 0.01f);
    EXPECT_FLOAT_EQ(stepper.getTargetSpeedStepsS(), (HOMING_FEEDRATE_FAST_XY / 60) * STEPS_PER_MM_XY);
    EXPECT_FLOAT_EQ(stepper.getAccelStepsS2(), ACCEL_XY_MM_S2 * STEPS_PER_MM_XY);
    EXPECT_NEAR(stepper.getMinSpeedStepsS(), (MIN_SPEED_MM_MIN / 60.0f) * STEPS_PER_MM_XY, 0.01f);

    EXPECT_TRUE(mocktimer.IT_run);
    EXPECT_NEAR(mocktimer.period_reg, TIMER_CLOCK_HZ / currentSpeedStepsS, 0.1f);
    EXPECT_EQ(mocktimer.counter_reg, 0);
}

TEST_F(StepperTest, OnTimer0Steps) {
    stepper.setStepsRemaining(0);
    EXPECT_EQ(stepper.getStepCount(), 0);

    stepper.onTimer();
    EXPECT_EQ(mocksys.NOP_calls, 0);
    EXPECT_FALSE(mocktimer.IT_run);
}

TEST_F(StepperTest, OnTimerCalcsFwd) {
    float mm = 20.0f;
    stepper.move(mm, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    int32_t stepsTotal = stepper.getStepsRemaining();
    stepper.onTimer();
    EXPECT_EQ(mocksys.NOP_calls, 8);
    EXPECT_EQ(stepper.getStepCount(), 1);
    EXPECT_EQ(stepper.getStepsRemaining(), stepsTotal - 1);
}

TEST_F(StepperTest, OnTimerCalcsRev) {
    float mm = -20.0f;
    stepper.move(mm, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    int32_t stepsTotal = stepper.getStepsRemaining();
    stepper.onTimer();
    EXPECT_EQ(mocksys.NOP_calls, 8);
    EXPECT_EQ(stepper.getStepCount(), -1);
    EXPECT_EQ(stepper.getStepsRemaining(), stepsTotal - 1);
}

TEST_F(StepperTest, OnTimerEnvelope) {
    // run the move calcs again
    float mm = 20.0f;
    stepper.move(mm, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    float targetSpeedStepsS = (HOMING_FEEDRATE_FAST_XY / 60) * STEPS_PER_MM_XY;  // 8,000
    EXPECT_FLOAT_EQ(stepper.getTargetSpeedStepsS(), (HOMING_FEEDRATE_FAST_XY / 60) * STEPS_PER_MM_XY);
    float minSpeedStepsS = (MIN_SPEED_MM_MIN / 60.0f) * STEPS_PER_MM_XY; // 133.33
    EXPECT_NEAR(stepper.getMinSpeedStepsS(), minSpeedStepsS, 0.01f);
    int32_t stepsTotal = stepper.getStepsRemaining();
    EXPECT_EQ(stepsTotal, STEPS_PER_MM_XY * std::abs(mm));  // steps remaining before moving
    float currentSpeedStepsS = stepper.getCurrentSpeedStepsS();
    EXPECT_NEAR(currentSpeedStepsS, minSpeedStepsS, 0.01f);
    EXPECT_NEAR(mocktimer.period_reg, (TIMER_CLOCK_HZ / currentSpeedStepsS), 0.01f);

    // move sequence to last step of accel and check step count
    while (stepper.getCurrentSpeedStepsS() < stepper.getTargetSpeedStepsS()) { stepper.onTimer(); }
    int32_t accelStepsExpected = calcAccelSteps(HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    int32_t stepCount = stepper.getStepCount();
    EXPECT_NEAR(accelStepsExpected, stepCount, 10.0f);

    // move sequence to 1st step of decel and check step count
    while (stepper.getCurrentSpeedStepsS() >= stepper.getTargetSpeedStepsS()) { stepper.onTimer(); }
    stepCount = stepper.getStepCount();
    EXPECT_NEAR(stepsTotal - accelStepsExpected, stepCount, 10.0f);

    // move sequence to last step of move and check the finish
    while (stepper.isMoving()) { stepper.onTimer(); }
    EXPECT_EQ(mocktimer.IT_run, 0);
    EXPECT_EQ(stepper.getStepsRemaining(), 0);
    EXPECT_FLOAT_EQ(stepper.getCurrentSpeedStepsS(), 0.0f);
}

TEST_F(StepperTest, StopDuringMove) {
    float mm = 20.0f;
    stepper.move(mm, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    while (stepper.getStepCount() < 500) { stepper.onTimer(); }
    stepper.stop();
    EXPECT_EQ(mocktimer.IT_run, 0);
    EXPECT_EQ(stepper.getStepsRemaining(), 0);
    EXPECT_FLOAT_EQ(stepper.getCurrentSpeedStepsS(), 0.0f);
}
