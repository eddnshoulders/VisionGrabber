#include <gtest/gtest.h>
#include "MockTimer.h"
#include "MockGPIO.h"
#include "MockSYS.h"
#include "Stepper.h"
#include "CoreXY.h"
#include "Config.h"
#include <cmath>
#include <iostream>

// test fixture class
class CoreXYTest : public ::testing::Test {
protected:
    MockTimer mocktimer_a;
    MockTimer mocktimer_b;
    MockGPIO mockgpio_en_a;
    MockGPIO mockgpio_en_b;
    MockGPIO mockgpio_dir_a;
    MockGPIO mockgpio_dir_b;
    MockGPIO mockgpio_step_a;
    MockGPIO mockgpio_step_b;
    MockSYS mocksys;
    Stepper stepper_a;
    Stepper stepper_b;
    CoreXY corexy;

    CoreXYTest()
      : stepper_a(mocktimer_a, mockgpio_en_a, mockgpio_dir_a, mockgpio_step_a, mocksys, STEPS_PER_MM_XY, false),
        stepper_b(mocktimer_b, mockgpio_en_b, mockgpio_dir_b, mockgpio_step_b, mocksys, STEPS_PER_MM_XY, false),
        corexy(stepper_a, stepper_b, STEPS_PER_MM_XY) {}
};

TEST_F(CoreXYTest, Enable) {
    corexy.enable();
    EXPECT_TRUE(stepper_a.checkEnabled());
    EXPECT_TRUE(stepper_b.checkEnabled());
}

TEST_F(CoreXYTest, Disable) {
    corexy.disable();
    EXPECT_FALSE(stepper_a.checkEnabled());
    EXPECT_FALSE(stepper_b.checkEnabled());
}

TEST_F(CoreXYTest, Stop) {
    corexy.move(20.0f, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_TRUE(mocktimer_a.IT_run);
    EXPECT_GT(stepper_a.getStepsRemaining(), 0);
    EXPECT_TRUE(mocktimer_b.IT_run);
    EXPECT_GT(stepper_b.getStepsRemaining(), 0);
    corexy.stop();
    EXPECT_FALSE(mocktimer_a.IT_run);
    EXPECT_EQ(stepper_a.getStepsRemaining(), 0);
    EXPECT_FALSE(mocktimer_b.IT_run);
    EXPECT_EQ(stepper_b.getStepsRemaining(), 0);
}

TEST_F(CoreXYTest, SetPosition) {
    float X = 60;
    float Y = 30;
    corexy.setPosition(X, Y);
    EXPECT_FLOAT_EQ(corexy.getX(), X);
    EXPECT_FLOAT_EQ(corexy.getY(), Y);
}

TEST_F(CoreXYTest, IsMovingEither) {
    corexy.move(20.0f, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_TRUE(corexy.isMoving());
}

TEST_F(CoreXYTest, IsMovingNeither) {
    corexy.move(20.0f, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    corexy.stop();
    EXPECT_FALSE(corexy.isMoving());
}

TEST_F(CoreXYTest, MoveXOnly) {
    corexy.move(20.0f, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    while (corexy.isMoving()) {
        stepper_a.onTimer();
        stepper_b.onTimer();
    }
    EXPECT_EQ(stepper_a.getStepCount(), stepper_b.getStepCount());
    EXPECT_FLOAT_EQ(corexy.getX(), 20.0f);
    EXPECT_FLOAT_EQ(corexy.getY(), 0.0f);
}

TEST_F(CoreXYTest, MoveYOnly) {
    corexy.move(0.0f, 20.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    while (corexy.isMoving()) {
        stepper_a.onTimer();
        stepper_b.onTimer();
    }
    EXPECT_EQ(stepper_a.getStepCount(), 20.0f * STEPS_PER_MM_XY);
    EXPECT_EQ(stepper_b.getStepCount(), -20.0f * STEPS_PER_MM_XY);
    EXPECT_FLOAT_EQ(corexy.getX(), 0.0f);
    EXPECT_FLOAT_EQ(corexy.getY(), 20.0f);
}

TEST_F(CoreXYTest, MoveDiag) {
    corexy.move(20.0f, 20.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    while (corexy.isMoving()) {
        stepper_a.onTimer();
        stepper_b.onTimer();
    }
    EXPECT_EQ(stepper_a.getStepCount(), 2 * (20.0f * STEPS_PER_MM_XY));
    EXPECT_EQ(stepper_b.getStepCount(), 0);
    EXPECT_FLOAT_EQ(corexy.getX(), 20.0f);
    EXPECT_FLOAT_EQ(corexy.getY(), 20.0f);
}

TEST_F(CoreXYTest, MoveZero) {
    corexy.move(0.0f, 0.0f, HOMING_FEEDRATE_FAST_XY, ACCEL_XY_MM_S2);
    EXPECT_FALSE(stepper_a.isMoving());
    EXPECT_FALSE(stepper_b.isMoving());
}

TEST_F(CoreXYTest, MoveFeedrateScaling) {
    corexy.move(80.0f, 40.0f, 3000.0f, ACCEL_XY_MM_S2);
    EXPECT_FLOAT_EQ(stepper_a.getFeedrateMMS(), 50.0f);
    EXPECT_NEAR(stepper_b.getFeedrateMMS(), 16.67f, 0.01f);
}

