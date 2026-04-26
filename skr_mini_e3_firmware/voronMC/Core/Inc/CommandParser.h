/*
 * CommandParser.h
 *
 *  Created on: 30 Mar 2026
 *      Author: f402n
 */

#ifndef SRC_COMMANDPARSER_H_
#define SRC_COMMANDPARSER_H_

#pragma once
#include <cstdint>
#include <cstring>

constexpr uint8_t CMD_BUFFER_SIZE = 64;

struct ParsedCommand {
	char cmd[8];
	float x, y, z, f, s, p;
	bool has_x, has_y, has_z, has_f, has_s, has_p;
	bool error = false;
};
class CommandParser {
public:
	CommandParser(void);
	virtual ~CommandParser(void);
	bool processByte(uint8_t byte);		// called from UART RX callback for each byte. True when command is completed
	ParsedCommand getCommand(void);
	void reset(void);
private:
	char buf_[CMD_BUFFER_SIZE];
	uint8_t len_ = 0;
	ParsedCommand parsed_;

	bool parseLine(void);
};

#endif /* SRC_COMMANDPARSER_H_ */
