/*
 * MockTimer.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef MOCKS_MOCKTIMER_H_
#define MOCKS_MOCKTIMER_H_

#include <IHAL/ITimer.h>
#include <cstdint>

class MockTimer : public ITimer {
public:
	void Start_PWM(void) override { PWM_run = true; }
	void Stop_PWM(void) override { PWM_run = false; }
	void Start_IT(void) override { IT_run = true; }
	void Stop_IT(void) override { IT_run = false; }
	void writeCompareReg(uint32_t value) override { CCR_reg = value; }
	void setARRPeriod(uint32_t period) override { period_reg = period; }
	void setCounter(uint32_t count) override { counter_reg = count; }

	bool PWM_run = false;
	bool IT_run = false;
	uint32_t CCR_reg = 0;
	uint32_t period_reg = 0;
	uint32_t counter_reg = 0;
};

#endif /* MOCKS_MOCKTIMER_H_ */
