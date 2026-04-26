/*
 * GPIOImp.h
 *
 *  Created on: 5 Apr 2026
 *      Author: f402n
 */

#ifndef INC_GPIOIMP_H_
#define INC_GPIOIMP_H_

#include <IHAL/IGPIO.h>
#include "main.h"


class GPIOImp : public IGPIO {
public:
	GPIOImp(GPIO_TypeDef* port, uint16_t pin);

	void setPin(void) override;
	void resetPin(void) override;
	bool readPin(void) override;
	void togglePin(void) override;
	IGPIO_StatusTypeDef lockPin() override;

	virtual ~GPIOImp(void);

private:
	GPIO_TypeDef* port_;
	uint16_t pin_;
};

#endif /* INC_GPIOIMP_H_ */
