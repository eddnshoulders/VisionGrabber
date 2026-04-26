/*
 * Servo.cpp
 *
 *  Created on: 31 Mar 2026
 *      Author: f402n
 */

// Servo.cpp
#include "Servo.h"
#include "Config.h"
#include <algorithm>

// value clamping template function
template<typename T>
static inline T clamp(T val, T lo, T hi) {
    return val < lo ? lo : (val > hi ? hi : val);
}

Servo::Servo(ITimer& itimer,
			 uint16_t min_pulse_us,
			 uint16_t max_pulse_us)
    			: itimer_(itimer),
				  min_pulse_us_(min_pulse_us),
				  max_pulse_us_(max_pulse_us) {}

void Servo::init(void) { itimer_.Start_PWM(); }
void Servo::detach(void) { itimer_.Stop_PWM(); }

void Servo::setAngle(float degrees)
{
	degrees = clamp(degrees, 0.0f, 180.0f);
    float us = min_pulse_us_ + (degrees / 180.0f) * (max_pulse_us_ - min_pulse_us_);
    setPulseUs((uint16_t)us);
}

void Servo::setPulseUs(uint16_t us)
{
	us = clamp(us, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
    itimer_.writeCompareReg((uint32_t)us);
}

Servo::~Servo(void) = default;
