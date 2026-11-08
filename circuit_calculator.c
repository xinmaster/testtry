#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#define INPUT_BUFFER_SIZE 256
#define MAX_RESISTORS 1000

typedef enum {
    READ_END,
    READ_OK,
    READ_INVALID
} ReadStatus;

/* Read and consume the entire line, including an invalid line's excess bytes. */
static ReadStatus read_line(char *buffer, size_t capacity)
{
    size_t used = 0;
    bool saw_input = false;
    bool invalid = false;
    int ch;

    while ((ch = getchar()) != EOF && ch != '\n') {
        saw_input = true;
        if (ch == '\0') {
            invalid = true;
        }
        if (used + 1 < capacity) {
            buffer[used++] = (char)ch;
        } else {
            invalid = true;
        }
    }
    buffer[used] = '\0';

    if (ferror(stdin)) {
        fputs("读取输入失败。\n", stderr);
        exit(EXIT_FAILURE);
    }
    if (ch == EOF && !saw_input) {
        return READ_END;
    }
    if (invalid) {
        printf("输入错误：每行最多 %d 个字节，且不能包含空字符。\n",
               INPUT_BUFFER_SIZE - 1);
        return READ_INVALID;
    }
    return READ_OK;
}

static bool only_whitespace(const char *text)
{
    while (isspace((unsigned char)*text)) {
        ++text;
    }
    return *text == '\0';
}

static bool read_integer(const char *prompt, long minimum, long maximum,
                         long *value)
{
    char line[INPUT_BUFFER_SIZE];

    for (;;) {
        char *end;
        long number;
        ReadStatus status;

        fputs(prompt, stdout);
        fflush(stdout);
        status = read_line(line, sizeof line);
        if (status == READ_END) {
            return false;
        }
        if (status == READ_INVALID) {
            continue;
        }

        errno = 0;
        number = strtol(line, &end, 10);
        if (end == line || !only_whitespace(end) || errno != 0 ||
            number < minimum || number > maximum) {
            printf("输入错误：请输入 %ld 到 %ld 之间的整数。\n",
                   minimum, maximum);
            continue;
        }
        *value = number;
        return true;
    }
}

static bool read_number(const char *prompt, bool strictly_positive,
                        double *value)
{
    char line[INPUT_BUFFER_SIZE];

    for (;;) {
        char *end;
        double number;
        ReadStatus status;

        fputs(prompt, stdout);
        fflush(stdout);
        status = read_line(line, sizeof line);
        if (status == READ_END) {
            return false;
        }
        if (status == READ_INVALID) {
            continue;
        }

        errno = 0;
        number = strtod(line, &end);
        if (end == line || !only_whitespace(end) || errno != 0 ||
            !isfinite(number) || number < 0.0 ||
            (strictly_positive && number == 0.0)) {
            printf("输入错误：请输入%s的有限数值，不要附带单位，"
                   "且数值须在 double 的解析范围内。\n",
                   strictly_positive ? "大于 0" : "大于或等于 0");
            continue;
        }
        /* Treat negative zero as zero when displaying magnitude results. */
        *value = number == 0.0 ? 0.0 : number;
        return true;
    }
}

static void print_result(double result, const char *unit, bool positive_expected)
{
    if (!isfinite(result) || (positive_expected && result == 0.0)) {
        puts("计算错误：结果超出 double 可表示的范围（溢出或下溢）。");
        return;
    }
    printf("计算结果：%.10g %s\n", result, unit);
}

static bool calculate_ohm(long choice)
{
    double voltage;
    double current;
    double resistance;

    switch (choice) {
    case 1:
        if (!read_number("请输入电流 I（A，>= 0）：", false, &current) ||
            !read_number("请输入电阻 R（Ω，>= 0）：", false, &resistance)) {
            return false;
        }
        /* Ohm's law: V = I * R. */
        print_result(current * resistance, "V",
                     current > 0.0 && resistance > 0.0);
        break;
    case 2:
        if (!read_number("请输入电压 V（V，>= 0）：", false, &voltage) ||
            !read_number("请输入电阻 R（Ω，> 0）：", true, &resistance)) {
            return false;
        }
        print_result(voltage / resistance, "A", voltage > 0.0);
        break;
    case 3:
        if (!read_number("请输入电压 V（V，>= 0）：", false, &voltage) ||
            !read_number("请输入电流 I（A，> 0）：", true, &current)) {
            return false;
        }
        print_result(voltage / current, "Ω", voltage > 0.0);
        break;
    default:
        return false;
    }
    return true;
}

static bool calculate_resistors(bool parallel)
{
    double resistances[MAX_RESISTORS] = {0.0};
    long count;

    if (!read_integer("请输入电阻数量（1 到 1000）：", 1, MAX_RESISTORS,
                      &count)) {
        return false;
    }
    for (long i = 0; i < count; ++i) {
        char prompt[96];
        snprintf(prompt, sizeof prompt, "请输入第 %ld 个电阻（Ω，>= 0）：",
                 i + 1);
        if (!read_number(prompt, false, &resistances[i])) {
            return false;
        }
    }

    if (parallel) {
        double minimum = resistances[0];
        double scaled_sum = 0.0;

        for (long i = 1; i < count; ++i) {
            if (resistances[i] < minimum) {
                minimum = resistances[i];
            }
        }
        /* A zero-ohm branch short-circuits the whole parallel network. */
        if (minimum == 0.0) {
            print_result(0.0, "Ω", false);
            return true;
        }
        /* R_eq = min(R) / sum(min(R) / R_i); no large reciprocals needed. */
        for (long i = 0; i < count; ++i) {
            scaled_sum += minimum / resistances[i];
        }
        print_result(minimum / scaled_sum, "Ω", true);
    } else {
        double total = 0.0;

        for (long i = 0; i < count; ++i) {
            total += resistances[i];
            if (!isfinite(total)) {
                break;
            }
        }
        print_result(total, "Ω", false);
    }
    return true;
}

static void print_menu(void)
{
    puts("\n===== 基础电路计算器 =====");
    puts("1. 欧姆定律：计算电压 V = I × R");
    puts("2. 欧姆定律：计算电流 I = V / R");
    puts("3. 欧姆定律：计算电阻 R = V / I");
    puts("4. 计算串联等效电阻");
    puts("5. 计算并联等效电阻");
    puts("0. 退出");
    puts("单位：V、A、Ω；按非负幅值计算，每次输入一个数值。");
}

int main(void)
{
    for (;;) {
        long choice;
        bool completed;

        print_menu();
        if (!read_integer("请选择计算项目（0 到 5）：", 0, 5, &choice)) {
            break;
        }
        if (choice == 0) {
            puts("感谢使用，再见！");
            return EXIT_SUCCESS;
        }

        if (choice <= 3) {
            completed = calculate_ohm(choice);
        } else {
            completed = calculate_resistors(choice == 5);
        }
        if (!completed) {
            break;
        }
    }
    puts("\n输入结束，程序退出。");
    return EXIT_SUCCESS;
}
