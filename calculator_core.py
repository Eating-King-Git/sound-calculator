"""Decimal calculator state and arithmetic, independent of Tk and audio.

Operators have conventional precedence. Unary keys affect only the current
operand. No expression is passed to Python's evaluator.
"""

from __future__ import annotations

from decimal import Context, Decimal, DecimalException, DivisionByZero, InvalidOperation, localcontext


PRECISION = 28
MAX_INPUT_DIGITS = 24
MAX_TOKENS = 64
MAX_MAGNITUDE = Decimal("1e99")
MIN_MAGNITUDE = Decimal("1e-99")
ARITHMETIC_CONTEXT = Context(prec=PRECISION, Emin=-999, Emax=999)
OPERATORS = frozenset("+-*/")


class CalculationError(ValueError):
    """An arithmetic or input limit that can be shown to the user."""


def _bounded(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise CalculationError("结果不是有限实数")
    magnitude = value.copy_abs()
    if magnitude > MAX_MAGNITUDE or (magnitude and magnitude < MIN_MAGNITUDE):
        raise CalculationError("结果超出范围（1e-99 至 1e99）")
    return Decimal(0) if not value else value


def _canonical(value: Decimal) -> str:
    """Keep all computed digits internally; trim unneeded fractional zeros."""
    with localcontext(ARITHMETIC_CONTEXT):
        value = _bounded(value)
        return str(value.normalize()) if value else "0"


def _display_number(text: str, *, preserve_input: bool = False) -> str:
    # Preserve input such as '1.' and '-0' while it is being edited.
    if preserve_input:
        return text
    with localcontext(ARITHMETIC_CONTEXT):
        value = Decimal(text)
        expanded = format(value, "f")
        if "." in expanded:
            expanded = expanded.rstrip("0").rstrip(".")
        if len(expanded) <= 24:
            return expanded
        mantissa, exponent = format(value, ".15E").split("E")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}E{int(exponent):+d}"


def evaluate_tokens(tokens: list[str]) -> Decimal:
    """Evaluate an alternating number/operator sequence with * and / first."""
    if not tokens or len(tokens) % 2 != 1 or len(tokens) > MAX_TOKENS:
        raise CalculationError("算式不完整或过长")
    with localcontext(ARITHMETIC_CONTEXT):
        try:
            numbers = [_bounded(Decimal(tokens[i])) for i in range(0, len(tokens), 2)]
            operators = tokens[1::2]
            if any(operator not in OPERATORS for operator in operators):
                raise CalculationError("不支持的运算符")
            # Accumulate multiplicative terms, then apply additions/subtractions
            # left-to-right; division is also left-associative.
            total = Decimal(0)
            term = numbers[0]
            additive = "+"
            for operator, number in zip(operators, numbers[1:]):
                if operator == "*":
                    term = _bounded(term * number)
                elif operator == "/":
                    term = _bounded(term / number)
                else:
                    total = _bounded(total + term if additive == "+" else total - term)
                    additive, term = operator, number
            return _bounded(total + term if additive == "+" else total - term)
        except DivisionByZero as exc:
            raise CalculationError("不能除以零") from exc
        except InvalidOperation as exc:
            raise CalculationError("无效的算式或运算") from exc
        except DecimalException as exc:
            raise CalculationError("计算超出支持范围") from exc


class CalculatorModel:
    """Button-driven calculator with independent expression and operand state.

    ``C`` resets the current calculation but retains the last ten successful
    equality results. Repeated ``=`` is a no-op. Backspace edits only typed
    current input; on a computed operand it starts that operand again at zero.
    """

    def __init__(self) -> None:
        self.history: list[str] = []
        self.clear()

    def clear(self) -> None:
        self._tokens: list[str] = []
        self._current = "0"
        self._awaiting_operand = False
        self._has_input = False
        self._replace_input = True
        self._result_mode = False
        self._last_expression = ""
        self.error: str | None = None

    @property
    def display(self) -> str:
        return "错误" if self.error else _display_number(
            self._current, preserve_input=not self._replace_input and not self._result_mode
        )

    @property
    def expression(self) -> str:
        if self._result_mode:
            return self._last_expression + " ="
        values = self._tokens if self._awaiting_operand else self._tokens + [self._current]
        return " ".join(values).replace("*", "×").replace("/", "÷")

    def press(self, key: str) -> None:
        """Process a supported button; unrelated keys are ignored."""
        if not isinstance(key, str) or key not in {
            *"0123456789.+-*/", "=", "C", "Backspace", "±", "%", "√"
        }:
            return
        if key == "C":
            self.clear()
            return
        if self.error:
            if key in "0123456789.":
                self.clear()
            elif key == "Backspace":
                self.clear()
                return
            else:
                return
        try:
            if key in "0123456789.":
                self._digit(key)
            elif key in OPERATORS:
                self._operator(key)
            elif key == "=":
                self._equals()
            elif key == "Backspace":
                self._backspace()
            else:
                self._unary(key)
        except CalculationError as exc:
            self.error = str(exc)
        except DivisionByZero:
            self.error = "不能除以零"
        except DecimalException:
            self.error = "无效运算或结果超出范围"

    def _digit(self, key: str) -> None:
        if self._result_mode:
            self.clear()
        if self._replace_input or self._awaiting_operand:
            current = "0." if key == "." else key
        elif key == ".":
            if "." in self._current:
                return
            current = self._current + "."
        elif self._current in ("0", "-0"):
            current = ("-" if self._current.startswith("-") else "") + key
        else:
            current = self._current + key
        if sum(character.isdigit() for character in current) > MAX_INPUT_DIGITS:
            raise CalculationError(f"每个输入最多 {MAX_INPUT_DIGITS} 位数字")
        self._current = current
        self._has_input = True
        self._awaiting_operand = False
        self._replace_input = False

    def _operator(self, key: str) -> None:
        if self._awaiting_operand:
            self._tokens[-1] = key
            return
        if len(self._tokens) + 3 > MAX_TOKENS:
            raise CalculationError("算式过长，请先计算或清除")
        self._tokens.extend([self._current, key])
        self._current = "0"
        self._awaiting_operand = True
        self._has_input = False
        self._replace_input = True
        self._result_mode = False

    def _equals(self) -> None:
        if self._result_mode or (not self._tokens and not self._has_input):
            return
        if self._awaiting_operand:
            raise CalculationError("请先输入最后一个操作数")
        expression = self.expression
        result = evaluate_tokens(self._tokens + [self._current])
        self._current = _canonical(result)
        self._tokens = []
        self._result_mode = True
        self._replace_input = True
        self._has_input = True
        self._last_expression = expression
        self.history.append(f"{expression} = {self.display}")
        self.history[:] = self.history[-10:]

    def _backspace(self) -> None:
        if self._awaiting_operand:
            return
        if self._result_mode:
            self.clear()
            return
        if self._replace_input:
            self._current = "0"
        else:
            self._current = self._current[:-1]
            if self._current in ("", "-"):
                self._current = "0"
        self._replace_input = False
        self._has_input = True

    def _unary(self, key: str) -> None:
        if key == "±":
            self._current = self._current[1:] if self._current.startswith("-") else "-" + self._current
            if self._awaiting_operand or not self._has_input:
                self._replace_input = False
        else:
            with localcontext(ARITHMETIC_CONTEXT):
                value = Decimal(self._current)
                if key == "√" and value < 0:
                    raise CalculationError("负数不能取实数平方根")
                value = value / 100 if key == "%" else value.sqrt()
                self._current = _canonical(_bounded(value))
            self._replace_input = True
        self._awaiting_operand = False
        self._has_input = True
        self._result_mode = False
