/*
 * CoreXY.h
 *
 *  Created on: 7 Apr 2026
 *      Author: f402n
 */

#ifndef COREXY_H_
#define COREXY_H_

#pragma once
#include "IClass/IStepper.h"
#include "IClass/ICoreXY.h"
#include "Config.h"

class CoreXY : public ICoreXY {
public:
    CoreXY(IStepper& istepper_a, IStepper& istepper_b, float steps_per_mm);

    void move(float dx_mm, float dy_mm, float feedrate_mm_min, float accel_mm_s) override;	// Command a move in X/Y space (mm, mm/min)
    float getX(void) const override;			// Get current X/Y position from A/B step counts
    float getY(void) const override;
    void setPosition(float x_mm, float y_mm) override;	// Zero position
    void stop(void) override;
    void enable(void) override;
    void disable(void) override;
    bool isMoving(void) const override;

    virtual ~CoreXY(void);

private:
    IStepper& istepper_a_;
    IStepper& istepper_b_;
    float steps_per_mm_;
};

#endif /* COREXY_H_ */
