/*
 * ICoreXY,h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_ICOREXY_H_
#define SRC_ICOREXY_H_

#include <cstdint>

class ICoreXY {
public:
    virtual void move(float dx_mm, float dy_mm, float feedrate_mm_min, float accel_mm_s) = 0;	// Command a move in X/Y space (mm, mm/min)
    virtual float getX(void) const = 0;			// Get current X/Y position from A/B step counts
    virtual float getY(void) const = 0;
    virtual void setPosition(float x_mm, float y_mm) = 0;	// Zero position
    virtual void stop(void) = 0;
    virtual void enable(void) = 0;
    virtual void disable(void) = 0;
    virtual bool isMoving(void) const = 0;

    virtual ~ICoreXY(void) = default;
};

#endif /* SRC_ICOREXY_H_ */
