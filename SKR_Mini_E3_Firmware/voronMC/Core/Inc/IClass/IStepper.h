/*
 * IStepper.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_ISTEPPER_H_
#define SRC_ISTEPPER_H_

#include <cstdint>

class IStepper{
public:
    virtual void enable(void) = 0;
    virtual bool checkEnabled(void) const = 0;
    virtual void disable(void) = 0;
    virtual void move(float mm, float feedrate_mm_min, float accel_mm_s2) = 0;
    virtual void stop(void) = 0;
    virtual void onTimer(void) = 0;
    virtual float getPosition(void) const = 0;
    virtual void  setPosition(float mm) = 0;
    virtual bool  isMoving(void) const = 0;
    virtual float getStepsPerMm(void) = 0;
    virtual bool getInvertDir(void) = 0;
    virtual int32_t getStepCount(void) = 0;
    virtual void setStepCount(int32_t step_count) = 0;
    virtual int32_t getStepsRemaining(void) = 0;
    virtual void setStepsRemaining(int32_t steps) = 0;
    virtual bool getDirection(void) = 0;
    virtual float getCurrentSpeedStepsS(void) = 0;
    virtual float getTargetSpeedStepsS(void) = 0;
    virtual float getAccelStepsS2(void) = 0;
    virtual float getMinSpeedStepsS(void) = 0;
    virtual float getStepsToStop(void) = 0;
    virtual void setInvertDir(bool invert_dir) = 0;
    virtual float getFeedrateMMS(void) = 0;

    virtual ~IStepper(void) = default;
};

#endif /* SRC_ISTEPPER_H_ */
