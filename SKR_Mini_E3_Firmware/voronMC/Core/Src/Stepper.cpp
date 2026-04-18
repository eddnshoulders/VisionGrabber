#include "Stepper.h"
#include <cmath>
#include <cstring>
#include <cstdio>

Stepper::Stepper(ITimer& itimer,
				 IGPIO& igpio_en, IGPIO& igpio_dir, IGPIO& igpio_step,
				 ISYS& isys,
                 float steps_per_mm,
                 bool invert_dir)
      : itimer_(itimer),
      igpio_en_(igpio_en), igpio_dir_(igpio_dir), igpio_step_(igpio_step),
	  isys_(isys),
      steps_per_mm_(steps_per_mm),
      invert_dir_(invert_dir),
      step_count_(0),
      steps_remaining_(0),
      direction_(true),
      current_speed_steps_s_(0.0f),
      target_speed_steps_s_(0.0f),
      accel_steps_s2_(0.0f),
	  min_speed_steps_s_(0.0f),
	  steps_to_stop_(0.0f),
      feedrate_mm_s_(0.0f) {}

void Stepper::enable(void) { igpio_en_.resetPin(); }
bool Stepper::checkEnabled(void) const { return !igpio_en_.readPin(); }
void Stepper::disable(void) { igpio_en_.setPin(); }

void Stepper::move(float mm, float feedrate_mm_min, float accel_mm_s2)
{
	/*
    float mm_per_s = feedrate_mm_min / 60.0f;
    float target_steps_s = mm_per_s * steps_per_mm_;
    uint32_t initial_period = (uint32_t)(TIMER_CLOCK_HZ / (MIN_SPEED_MM_MIN / 60.0f * steps_per_mm_));
    uint32_t target_period = (uint32_t)(TIMER_CLOCK_HZ / target_steps_s);

    char buf[96];
    snprintf(buf, sizeof(buf), "feed=%d mm_s=%d tgt_steps=%d init_p=%lu tgt_p=%lu\r\n",
             (int)feedrate_mm_min,
             (int)mm_per_s,
             (int)target_steps_s,
             initial_period,
             target_period);
    HAL_UART_Transmit(&huart2, (uint8_t*)buf, strlen(buf), 100);
	*/


	int32_t steps = (int32_t)(mm * steps_per_mm_);
    if (steps == 0) return;

    // Set direction
    direction_ = steps > 0;
    bool physical_dir = invert_dir_ ? !direction_ : direction_;

    physical_dir ? igpio_dir_.setPin() : igpio_dir_.resetPin();

    steps_remaining_ = steps > 0 ? steps : -steps;

    feedrate_mm_s_ = feedrate_mm_min / 60.0f;
    // Initialise speed profile
    current_speed_steps_s_ = (MIN_SPEED_MM_MIN / 60.f) * steps_per_mm_;
    target_speed_steps_s_  = feedrate_mm_s_ * steps_per_mm_;
    accel_steps_s2_        = accel_mm_s2 * steps_per_mm_;
    min_speed_steps_s_ = (MIN_SPEED_MM_MIN / 60.0f) * steps_per_mm_;

    // Set initial timer period from starting speed
    uint32_t period = (uint32_t)(TIMER_CLOCK_HZ / current_speed_steps_s_);

    itimer_.Stop_IT();
    itimer_.setARRPeriod(period);
    itimer_.setCounter(0);
    itimer_.Start_IT();
}

void Stepper::stop(void)
{
    itimer_.Stop_IT();
	steps_remaining_ = 0;
    current_speed_steps_s_ = 0.0f;
}

void Stepper::onTimer(void)
{
    if (steps_remaining_ == 0) {
        itimer_.Stop_IT();
        return;
    }

    // Step pulse
    igpio_step_.setPin();
    isys_.NOP(); isys_.NOP(); isys_.NOP(); isys_.NOP();
    isys_.NOP(); isys_.NOP(); isys_.NOP(); isys_.NOP();
    igpio_step_.resetPin();

    // Update position
    if (direction_) step_count_++;
    else            step_count_--;

    steps_remaining_--;

    if (steps_remaining_ == 0) {
        itimer_.Stop_IT();
        current_speed_steps_s_ = 0.0f;
        return;
    }

    // Trapezoidal speed profile
    steps_to_stop_ = ( (current_speed_steps_s_ * current_speed_steps_s_) -
                           (min_speed_steps_s_ * min_speed_steps_s_) )
                          / (2.0f * accel_steps_s2_);

    if ((float)steps_remaining_ <= steps_to_stop_) {
        // Decelerate
        current_speed_steps_s_ -= accel_steps_s2_ / current_speed_steps_s_;
        if (current_speed_steps_s_ < min_speed_steps_s_)
            current_speed_steps_s_ = min_speed_steps_s_;
    }
    else if (current_speed_steps_s_ < target_speed_steps_s_) {
        // Accelerate
        current_speed_steps_s_ += accel_steps_s2_ / current_speed_steps_s_;
        if (current_speed_steps_s_ > target_speed_steps_s_)
            current_speed_steps_s_ = target_speed_steps_s_;
    }

    // Update timer period for new speed
    uint32_t period = (uint32_t)(TIMER_CLOCK_HZ / current_speed_steps_s_);
    itimer_.setARRPeriod(period);
}

float Stepper::getPosition(void) const { return (float)step_count_ / steps_per_mm_; }
void Stepper::setPosition(float mm) { step_count_ = (int32_t)(mm * steps_per_mm_); }
bool Stepper::isMoving(void) const { return steps_remaining_ > 0; }
float Stepper::getStepsPerMm(void) { return steps_per_mm_; }
bool Stepper::getInvertDir(void) { return invert_dir_; }
int32_t Stepper::getStepCount(void) { return step_count_; }
void Stepper::setStepCount(int32_t count) { step_count_ = count; }
int32_t Stepper::getStepsRemaining(void) { return steps_remaining_; }
void Stepper::setStepsRemaining(int32_t steps) { steps_remaining_ = steps; }
bool Stepper::getDirection(void) { return direction_; }
float Stepper::getCurrentSpeedStepsS(void) { return current_speed_steps_s_; }
float Stepper::getTargetSpeedStepsS(void) { return target_speed_steps_s_; }
float Stepper::getAccelStepsS2(void) { return accel_steps_s2_; }
float Stepper::getMinSpeedStepsS(void) { return min_speed_steps_s_; }
float Stepper::getStepsToStop(void) { return steps_to_stop_; }
void Stepper::setInvertDir(bool invert_dir) { invert_dir_ = invert_dir; }
float Stepper::getFeedrateMMS(void) { return feedrate_mm_s_; }

Stepper::~Stepper(void) = default;
