/*
 * UARTImpT.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef INC_UARTIMP_H_
#define INC_UARTIMP_H_

#include <IHAL/IUART.h>
#include "main.h"

class UARTImp : public IUART {
public:
	UARTImp(UART_HandleTypeDef* huart, uint32_t timeout = 100);

	IUART_StatusTypeDef UART_Transmit(const uint8_t* msg, uint16_t len) override;
	IUART_StatusTypeDef UART_Receive(uint8_t* msg, uint16_t len) override;
    void flushRx() override;
	virtual ~UARTImp(void);

private:
	UART_HandleTypeDef* huart_;
	uint32_t timeout_;
};

#endif /* INC_UARTIMP_H_ */
