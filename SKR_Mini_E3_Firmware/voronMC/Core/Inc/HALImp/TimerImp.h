/*
 * TimerImp.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef INC_TIMERIMP_H_
#define INC_TIMERIMP_H_

#include <IHAL/ITimer.h>
#include "main.h"

class TimerImp : public ITimer  {
public:
	TimerImp(TIM_HandleTypeDef* tim, uint32_t channel = 0);

	void Start_PWM(void) override;
	void Stop_PWM(void) override;
	void Start_IT(void) override;
	void Stop_IT(void) override;
	void writeCompareReg(uint32_t value) override;
	void setARRPeriod(uint32_t period) override;
	void setCounter(uint32_t count) override;

	virtual ~TimerImp(void);

private:
	TIM_HandleTypeDef* tim_;
	uint32_t channel_;
};

#endif /* INC_TIMERIMP_H_ */
