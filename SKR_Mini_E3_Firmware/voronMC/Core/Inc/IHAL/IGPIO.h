/*
 * IGPIO.h
 *
 *  Created on: 5 Apr 2026
 *      Author: f402n
 */

#ifndef SRC_IGPIO_H_
#define SRC_IGPIO_H_

#include <cstdint>

typedef enum
{
  IGPIO_OK       = 0x00U,
  IGPIO_ERROR    = 0x01U,
  IGPIO_BUSY     = 0x02U,
  IGPIO_TIMEOUT  = 0x03U
} IGPIO_StatusTypeDef;

class IGPIO {
public:
	virtual void setPin() = 0;
	virtual void resetPin() = 0;
	virtual bool readPin() = 0;
	virtual void togglePin() = 0;
	virtual IGPIO_StatusTypeDef lockPin() = 0;

	virtual ~IGPIO(void) = default;
};

#endif /* SRC_IGPIO_H_ */
