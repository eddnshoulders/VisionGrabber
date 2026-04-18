/*
 * CoreXY.cpp
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#include "CoreXY.h"
#include <cmath>

CoreXY::CoreXY(IStepper& istepper_a, IStepper& istepper_b, float steps_per_mm)
    : istepper_a_(istepper_a),
      istepper_b_(istepper_b),
      steps_per_mm_(steps_per_mm)  {}

void CoreXY::move(float dx_mm, float dy_mm, float feedrate_mm_min, float accel_mm_s2)
{
    // Convert X/Y displacement to A/B steps
    float a_mm = dx_mm + dy_mm;
    float b_mm = dx_mm - dy_mm;

    // Scale feedrate for each motor
    // The faster axis must move at feedrate, slower scales proportionally
    float a_abs = fabsf(a_mm);
    float b_abs = fabsf(b_mm);
    float max_mm = (a_abs > b_abs) ? a_abs : b_abs;

    if (max_mm == 0.0f) return;

    float feedrate_a_ = feedrate_mm_min * (a_abs / max_mm);
    float feedrate_b_ = feedrate_mm_min * (b_abs / max_mm);

    // Start both motors
    if (a_abs > 0.0f) istepper_a_.move(a_mm, feedrate_a_, accel_mm_s2);
    if (b_abs > 0.0f) istepper_b_.move(b_mm, feedrate_b_, accel_mm_s2);
}

float CoreXY::getX(void) const
{
    // X = (A + B) / 2 in mm
    float a_mm = istepper_a_.getPosition();
    float b_mm = istepper_b_.getPosition();
    return (a_mm + b_mm) / 2.0f;
}

float CoreXY::getY(void) const
{
    // Y = (A - B) / 2 in mm
    float a_mm = istepper_a_.getPosition();
    float b_mm = istepper_b_.getPosition();
    return (a_mm - b_mm) / 2.0f;
}

void CoreXY::setPosition(float x_mm, float y_mm)
{
    // Convert X/Y to A/B and set each stepper
    istepper_a_.setPosition(x_mm + y_mm);
    istepper_b_.setPosition(x_mm - y_mm);
}

void CoreXY::stop(void)
{
    istepper_a_.stop();
    istepper_b_.stop();
}

void CoreXY::enable(void)
{
    istepper_a_.enable();
    istepper_b_.enable();
}

void CoreXY::disable(void)
{
    istepper_a_.disable();
    istepper_b_.disable();
}

bool CoreXY::isMoving(void) const { return istepper_a_.isMoving() || istepper_b_.isMoving(); }

CoreXY::~CoreXY() = default;
