/*
 * TimerImp.cpp
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#include <HALImp/TimerImp.h>


TimerImp::TimerImp(TIM_HandleTypeDef* tim, uint32_t channel)
		: tim_(tim),
		  channel_(channel) {}

void TimerImp::Start_PWM(void)  { HAL_TIM_PWM_Start(tim_, channel_); }
void TimerImp::Stop_PWM(void)   { HAL_TIM_PWM_Stop(tim_, channel_); }
void TimerImp::Start_IT(void)   { HAL_TIM_Base_Start_IT(tim_); }
void TimerImp::Stop_IT(void) { HAL_TIM_Base_Stop_IT(tim_); }

void TimerImp::writeCompareReg(uint32_t value) {
    switch (channel_) {
        case TIM_CHANNEL_1: tim_->Instance->CCR1 = value; break;
        case TIM_CHANNEL_2: tim_->Instance->CCR2 = value; break;
        case TIM_CHANNEL_3: tim_->Instance->CCR3 = value; break;
        case TIM_CHANNEL_4: tim_->Instance->CCR4 = value; break;
        default: break;
    }
}

void TimerImp::setARRPeriod(uint32_t period) { __HAL_TIM_SET_AUTORELOAD(tim_, period); }
void TimerImp::setCounter(uint32_t count) { __HAL_TIM_SET_COUNTER(tim_, count); }

TimerImp::~TimerImp(void) = default;

