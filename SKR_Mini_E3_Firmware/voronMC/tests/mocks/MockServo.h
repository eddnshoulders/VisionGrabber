/*
 * MockServo.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKSERVO_H_
#define MOCKS_MOCKSERVO_H_

#include "IClass/IServo.h"


class MockServo : public IServo {
public:
	void init(void) override { PWM_run = true; }
    void setAngle(float degrees) override { last_angle = degrees; }
    void setPulseUs(uint16_t us) override { CCR_us = us; }
    void detach(void) override { PWM_run = false; }

    bool PWM_run = false;
    float last_angle = 0;
    uint16_t CCR_us = 0;
};

#endif /* MOCKS_MOCKSERVO_H_ */
