/*
 * Servo.h
 *
 *  Created on: 31 Mar 2026
 *      Author: f402n
 */

#ifndef SRC_SERVO_H_
#define SRC_SERVO_H_

#pragma once
#include "IHAL/ITimer.h"
#include "IClass/IServo.h"
#include <cstdint>

class Servo : public IServo {
public:
    Servo(ITimer& itimer,
          uint16_t min_pulse_us = 100,
          uint16_t max_pulse_us = 2000);

    void init(void) override;
    void detach(void) override;
    void setAngle(float degrees) override;
    void setPulseUs(uint16_t us) override;

    virtual ~Servo(void);

private:
    ITimer&   itimer_;
    uint16_t  min_pulse_us_;
    uint16_t  max_pulse_us_;
};

#endif /* SRC_SERVO_H_ */
