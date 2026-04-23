/*
 * IUART.h
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_IUART_H_
#define SRC_IUART_H_

#include <cstdint>

typedef enum
{
  IUART_OK       = 0x00U,
  IUART_ERROR    = 0x01U,
  IUART_BUSY     = 0x02U,
  IUART_TIMEOUT  = 0x03U
} IUART_StatusTypeDef;


class IUART {
public:
	virtual IUART_StatusTypeDef UART_Transmit(const uint8_t* msg, uint16_t len) = 0;
	virtual IUART_StatusTypeDef UART_Receive(uint8_t* msg, uint16_t len) = 0;
    virtual void flushRx() = 0;
	virtual ~IUART(void) = default;
};

#endif /* SRC_IUART_H_ */
