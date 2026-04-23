#include <gtest/gtest.h>
#include "MockTimer.h"
#include "Servo.h"
#include "Config.h"

static float pwCalc(float angDes)
{
    float pwMin = (float)SERVO_MIN_PULSE_US;
    float pwMax = (float)SERVO_MAX_PULSE_US;
    float pwDiff = pwMax - pwMin;
    float angDiff = (float)180 - (float)0;
    float pw = pwMin + ((pwDiff / angDiff) * angDes);
    return pw;
}

class ServoTest : public ::testing::Test {
protected:
    MockTimer mocktimer;
    Servo servo;

    ServoTest()
	: servo(mocktimer, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US)
    {}
};

TEST_F(ServoTest, PulsewidthMinClamp)  {
    servo.setPulseUs(SERVO_MIN_PULSE_US - 10);
    EXPECT_EQ(mocktimer.CCR_reg, SERVO_MIN_PULSE_US);
}

TEST_F(ServoTest, PulsewidthMaxClamp) {
    servo.setPulseUs(SERVO_MAX_PULSE_US + 10);
    EXPECT_EQ(mocktimer.CCR_reg, SERVO_MAX_PULSE_US);
}

TEST_F(ServoTest, AngleMinClamp) {
    servo.setAngle((float)-10);
    EXPECT_EQ(mocktimer.CCR_reg, SERVO_MIN_PULSE_US);
}

TEST_F(ServoTest, AngleMaxClamp) {
    servo.setAngle((float)190);
    EXPECT_EQ(mocktimer.CCR_reg, SERVO_MAX_PULSE_US);
}

TEST_F(ServoTest, AngleToPulsewidthCalc) {
    servo.setAngle((float)90);
    EXPECT_EQ(mocktimer.CCR_reg, (uint32_t)pwCalc((float)90));
}

TEST_F(ServoTest, InitTest) {
    servo.init();
    EXPECT_TRUE(mocktimer.PWM_run);
}

TEST_F(ServoTest, DetachTest) {
    servo.init();
    servo.detach();
    EXPECT_FALSE(mocktimer.PWM_run);
}
