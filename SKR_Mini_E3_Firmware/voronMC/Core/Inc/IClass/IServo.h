/*
 * IServo.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_IServo_H_
#define SRC_IServo_H_

#include <cstdint>

class IServo {
public:
    virtual void init(void) = 0;
    virtual void detach(void) = 0;
    virtual void setAngle(float degrees) = 0;
    virtual void setPulseUs(uint16_t us) = 0;

    virtual ~IServo(void) = default;
};

#endif /* SRC_IServo_H_ */
