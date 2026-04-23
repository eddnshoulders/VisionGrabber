/*
 * UARTImp.cpp
 *
 *  Created on: 3 Apr 2026
 *      Author: f402n
 */

#include "HALImp/UARTImp.h"
#include <cstring>

UARTImp::UARTImp(UART_HandleTypeDef* huart, uint32_t timeout)
						: huart_(huart),
						  timeout_(timeout) {}

IUART_StatusTypeDef UARTImp::UART_Transmit(const uint8_t* msg, uint16_t len) {
	return (IUART_StatusTypeDef)HAL_UART_Transmit(huart_, msg, len, timeout_);
}

IUART_StatusTypeDef UARTImp::UART_Receive(uint8_t* msg, uint16_t len) {
	return (IUART_StatusTypeDef)HAL_UART_Receive(huart_, msg, len, timeout_);
}

void UARTImp::flushRx() {
    __HAL_UART_CLEAR_OREFLAG(huart_);	            // Clear overrun error flag
    volatile uint32_t tmp = huart_->Instance->DR;	// Read and discard DR to clear any pending byte
}

UARTImp::~UARTImp(void) = default;
