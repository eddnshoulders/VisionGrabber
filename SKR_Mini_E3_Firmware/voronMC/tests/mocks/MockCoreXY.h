/*
 * MockCoreXY.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKCOREXY_H_
#define MOCKS_MOCKCOREXY_H_

#include "IClass/ICoreXY.h"

class MockCoreXY : public ICoreXY {
public:
    void move(float dx_mm, float dy_mm, float feedrate_mm_min, float accel_mm_s) override {
        move_called = true;
        last_dx = dx_mm;
        last_dy = dy_mm;
        last_feedrate = feedrate_mm_min;
        moving = true;
    }

    float getX(void) const override { return x; }
    float getY(void) const override { return y; }
    void setPosition(float x_mm, float y_mm) override { x = x_mm; y = y_mm; }
    void stop(void) override { moving = false; }
    void enable(void) override { enabled = true; }
    void disable(void) override { enabled = false; }
    bool isMoving(void) const override { return moving; }

    // controllable state
    bool moving = false;
    bool enabled = false;
    bool move_called = false;
    float x = 0.0f;
    float y = 0.0f;
    float last_dx = 0.0f;
    float last_dy = 0.0f;
    float last_feedrate = 0.0f;
};

#endif /* MOCKS_MOCKCOREXY_H_ */
