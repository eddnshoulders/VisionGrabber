/*
 * MockStepper.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKSTEPPER_H_
#define MOCKS_MOCKSTEPPER_H_

#include "IClass/IStepper.h"
#include "Config.h"

class MockStepper : public IStepper {
public:
	// non-inherited methods --------------------------------------------------------

	// manual method to allow test to set moving state without giving steps
	void setMoving(bool moving) { stepsRemaining = moving ? 1 : 0; }

	// overriden methods from IStepper ----------------------------------------------
	void enable(void) override { enabled = true; }
    bool checkEnabled(void) const override { return enabled; }
    void disable(void) override { enabled = false; }
    bool isMoving(void) const override { return stepsRemaining > 0; }
    void setPosition(float mm) override { position = mm; }
    float getPosition(void) const override { return position; }
    void setStepsRemaining(int32_t steps) override { stepsRemaining = steps; }
    void move(float mm, float feedrate_mm_min, float accel_mm_s2) override { setStepsRemaining(mm * steps_per_mm); }
    void stop(void) override { setStepsRemaining(0); }

    // stub methods for pure virtuals from IStepper ---------------------------------
    void onTimer(void) override {}
    float getStepsPerMm(void) override { return steps_per_mm; }
    bool getInvertDir(void) override { return invert_dir; }
    int32_t getStepCount(void) override { return 0; }
    void setStepCount(int32_t step_count) override {}
    int32_t getStepsRemaining(void) override { return stepsRemaining; }
    bool getDirection(void) override { return true; }
    float getCurrentSpeedStepsS(void) override { return 0.0f; }
    float getTargetSpeedStepsS(void) override { return 0.0f; }
    float getAccelStepsS2(void) override { return 0.0f; }
    float getMinSpeedStepsS(void) override { return 0.0f; }
    float getStepsToStop(void) override { return 0.0f; }
    void setInvertDir(bool invert_dir) override { invert_dir = true; }
    float getFeedrateMMS(void) override { return 0.0f; }

    virtual ~MockStepper() = default;

    // variables --------------------------------------------------------------------
    float steps_per_mm = STEPS_PER_MM_XY;  // sensible default
    bool invert_dir = false;
    bool enabled = false;
    float position = 0.0f;
    int32_t stepsRemaining = 0;
};

#endif /* MOCKS_MOCKSTEPPER_H_ */
