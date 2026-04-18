/*
 * SYSImp.h
 *
 *  Created on: 5 Apr 2026
 *      Author: f402n
 */

#ifndef INC_SYSIMP_H_
#define INC_SYSIMP_H_

#include <IHAL/ISYS.h>
#include "main.h"

class SYSImp : public ISYS  {
public:
	SYSImp();

	void NOP(void) override;

	virtual ~SYSImp(void);
};

#endif /* INC_SYSIMP_H_ */
