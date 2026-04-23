#ifndef SRC_STEPPER_H_
#define SRC_STEPPER_H_

#pragma once
#include <IHAL/ITimer.h>
#include <IHAL/IGPIO.h>
#include <IHAL/ISYS.h>
#include "IClass/IStepper.h"
#include "Config.h"
#include <cstdint>
#include <cmath>

class Stepper : public IStepper {
public:
	Stepper(ITimer& itimer,
	        IGPIO& igpio_en,
			IGPIO& igpio_dir,
			IGPIO& igpio_step,
			ISYS& isys,
	        float steps_per_mm,
	        bool invert_dir);

    void enable(void);
    bool checkEnabled(void) const;
    void disable(void);
    void move(float mm, float feedrate_mm_min, float accel_mm_s2);
    void stop(void);
    void onTimer(void);

    float getPosition(void) const;
    void  setPosition(float mm);
    bool  isMoving(void) const;

    float getStepsPerMm(void);
    bool getInvertDir(void);
    int32_t getStepCount(void);
    void setStepCount(int32_t step_count);
    int32_t getStepsRemaining(void);
    void setStepsRemaining(int32_t steps);
    bool getDirection(void);
    float getCurrentSpeedStepsS(void);
    float getTargetSpeedStepsS(void);
    float getAccelStepsS2(void);
    float getMinSpeedStepsS(void);
    float getStepsToStop(void);
    void setInvertDir(bool invert_dir);
    float getFeedrateMMS(void);

    virtual ~Stepper(void);

private:
    ITimer& itimer_;
    IGPIO& igpio_en_;
    IGPIO& igpio_dir_;
    IGPIO& igpio_step_;
    ISYS& isys_;
    float         steps_per_mm_;
    bool          invert_dir_;

    volatile int32_t step_count_         = 0;
    volatile int32_t steps_remaining_    = 0;
    volatile bool    direction_          = true;

    float current_speed_steps_s_         = 0.0f;
    float target_speed_steps_s_          = 0.0f;
    float accel_steps_s2_                = 0.0f;
	float min_speed_steps_s_			 = 0.0f;
	float steps_to_stop_				 = 0.0f;
	float feedrate_mm_s_				 = 0.0f;
};

#endif /* SRC_STEPPER_H_ */
