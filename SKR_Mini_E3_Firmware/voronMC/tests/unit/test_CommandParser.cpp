#include <gtest/gtest.h>
#include "CommandParser.h"
using std::string;

// helper -- feeds a string into the parser byte by byte
// returns true if any byte triggered a completed command
static bool feed(CommandParser& parser, const char* str)
{
    bool result = false;
    for (const char* p = str; *p; p++) {
        result = parser.processByte(*p);
    }
    return result;
}

// ── processByte ───────────────────────────────────────────────────────────────

TEST(CommandParserTest, ReturnsFalseForNormalBytes)
{
    CommandParser parser;
    EXPECT_FALSE(parser.processByte('G'));
    EXPECT_FALSE(parser.processByte('2'));
    EXPECT_FALSE(parser.processByte('8'));
}

TEST(CommandParserTest, ReturnsFalseForCarriageReturn)
{
    CommandParser parser;
    EXPECT_FALSE(parser.processByte('\r'));
}

TEST(CommandParserTest, ReturnsTrueOnNewline)
{
    CommandParser parser;
    feed(parser, "G28");
    EXPECT_TRUE(parser.processByte('\n'));
}

// ── command word ──────────────────────────────────────────────────────────────

TEST(CommandParserTest, ParsesG28)
{
    CommandParser parser;
    bool result = feed(parser, "G28\n");
    EXPECT_TRUE(result);
    ParsedCommand cmd = parser.getCommand();
    EXPECT_STREQ(cmd.cmd, "G28");
}

TEST(CommandParserTest, ParsesG0)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X1.1 Y2.2 Z3.3 F100\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "G0");
    EXPECT_TRUE(cmd.has_x);
    EXPECT_FLOAT_EQ(cmd.x, 1.1f);
    EXPECT_TRUE(cmd.has_y);
    EXPECT_FLOAT_EQ(cmd.y, 2.2f);
    EXPECT_TRUE(cmd.has_z);
    EXPECT_FLOAT_EQ(cmd.z, 3.3f);
    EXPECT_TRUE(cmd.has_f);
    EXPECT_FLOAT_EQ(cmd.f, 100);
}

TEST(CommandParserTest, ParsesM400)
{
    CommandParser parser;
    bool result = feed(parser, "M400\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "M400");
}

TEST(CommandParserTest, ParsesSTOP)
{
    CommandParser parser;
    bool result = feed(parser, "STOP\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "STOP");
}

TEST(CommandParserTest, ParsesM114)
{
    CommandParser parser;
    bool result = feed(parser, "M114\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "M114");
}

TEST(CommandParserTest, ParsesM280)
{
    CommandParser parser;
    bool result = feed(parser, "M280 S90 P1000\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "M280");
    EXPECT_TRUE(cmd.has_s);
    EXPECT_FLOAT_EQ(cmd.s, 90.0f);
    EXPECT_TRUE(cmd.has_p);
    EXPECT_FLOAT_EQ(cmd.p, 1000.0f);
}

TEST(CommandParserTest, ConvertsToUppercase)
{
    CommandParser parser;
    bool result = feed(parser, "g28\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "G28");
}

// ── parameter parsing ─────────────────────────────────────────────────────────

TEST(CommandParserTest, ParsesXParameter)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X12.5\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_TRUE(cmd.has_x);
    EXPECT_FLOAT_EQ(cmd.x, 12.5f);
}

TEST(CommandParserTest, ParsesMultipleParameters)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X10 Y20 Z5\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_TRUE(cmd.has_x);
    EXPECT_TRUE(cmd.has_y);
    EXPECT_TRUE(cmd.has_z);
    EXPECT_FLOAT_EQ(cmd.x, 10.0f);
    EXPECT_FLOAT_EQ(cmd.y, 20.0f);
    EXPECT_FLOAT_EQ(cmd.z, 5.0f);
}

TEST(CommandParserTest, HasFlagsNotSetForMissingParameters)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X10\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_TRUE(cmd.has_x);
    EXPECT_FALSE(cmd.has_y);
    EXPECT_FALSE(cmd.has_z);
}

TEST(CommandParserTest, ParsesNegativeValue)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X-5.5\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_TRUE(cmd.has_x);
    EXPECT_FLOAT_EQ(cmd.x, -5.5f);
}

// ── edge cases ────────────────────────────────────────────────────────────────

TEST(CommandParserTest, EmptyLineReturnsFalse)
{
    CommandParser parser;
    EXPECT_FALSE(parser.processByte('\n'));
}

TEST(CommandParserTest, GetCommandResetsState)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X10\n");
    parser.getCommand();
    // second getCommand should return empty
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(result);
    EXPECT_STREQ(cmd.cmd, "");
    EXPECT_FALSE(cmd.has_x);
}

TEST(CommandParserTest, BufferFullDropsExcessBytes)
{
    CommandParser parser;
    std::string long_cmd(65, 'A');
    long_cmd += '\n';
    bool result = feed(parser, long_cmd.c_str());
    ParsedCommand cmd = parser.getCommand();
    EXPECT_FALSE(result);
    EXPECT_STREQ(cmd.cmd, "AAAAAAA");
    EXPECT_FALSE(cmd.has_x);
    EXPECT_FALSE(cmd.has_y);
    EXPECT_FALSE(cmd.has_z);
    EXPECT_FALSE(cmd.has_f);
    EXPECT_FALSE(cmd.has_s);
    EXPECT_FALSE(cmd.has_p);
}

TEST(CommandParserTest, MalformedFloatRejectsCommand)
{
    CommandParser parser;
    bool result = feed(parser, "G0 X0,2\n");
    EXPECT_FALSE(result);
}

TEST(CommandParserTest, MalformedParameterAssignmentSyntax)
{
    CommandParser parser;
    feed(parser, "G0 X120 Y=120 F10000\n");
    ParsedCommand cmd = parser.getCommand();
    EXPECT_TRUE(cmd.error);
}
