import typing
from copy import deepcopy


class BoolPoly:
    def __init__(
        self,
        const: bool,
        linear: typing.Set[int],
        nonlinear: typing.Set[typing.FrozenSet[int]],
        rdc_src: "BoolPolySystem" = None,
    ) -> None:
        self.const = bool(const)
        self.linear = deepcopy(linear)
        self.nonlinear = deepcopy(nonlinear)
        self.rdc_src = rdc_src

    def __xor__(self, other: typing.Union["BoolPoly", int]) -> "BoolPoly":
        if isinstance(other, BoolPoly):
            res = BoolPoly(
                self.const ^ other.const,
                self.linear ^ other.linear,
                self.nonlinear ^ other.nonlinear,
            )
        elif isinstance(other, int):
            res = BoolPoly(self.const ^ other, self.linear, self.nonlinear)
        else:
            raise TypeError("Unsupported type for xor operation")
        return res if self.rdc_src is None else self.rdc_src.rdc(res)

    def __and__(self, other: "BoolPoly") -> "BoolPoly":
        linear = (self.linear if other.const else set()) ^ (
            other.linear if self.const else set()
        )
        nonlinear = (self.nonlinear if other.const else set()) ^ (
            other.nonlinear if self.const else set()
        )
        for var1 in self.linear:
            for var2 in other.linear:
                if var1 == var2:
                    linear ^= {var1}
                else:
                    nonlinear ^= {frozenset({var1, var2})}
        for var in self.linear:
            for mono in other.nonlinear:
                nonlinear ^= {mono | {var}}
        for var in other.linear:
            for mono in self.nonlinear:
                nonlinear ^= {mono | {var}}
        for mono1 in self.nonlinear:
            for mono2 in other.nonlinear:
                nonlinear ^= {mono1 | mono2}

        return BoolPoly(
            self.const & other.const,
            linear,
            nonlinear,
        )

    def __setitem__(self, key: int, value: bool) -> None:
        if value:
            if key in self.linear:
                self.linear.remove(key)
                self.const ^= 1
            new_nonlinear = set()
            for mono in self.nonlinear:
                if key in mono:
                    new_mono = mono - set([key])
                    if len(new_mono) == 1:
                        self.linear.add(set(new_mono).pop())
                    else:
                        new_nonlinear.add(new_mono)
                else:
                    new_nonlinear.add(mono)
        else:
            self.linear.discard(key)
            self.nonlinear = set(mono for mono in self.nonlinear if key not in mono)

    def __invert__(self) -> "BoolPoly":
        return BoolPoly(not self.const, self.linear, self.nonlinear)

    def __le__(self, other: "BoolPoly") -> bool:
        return self.linear <= other.linear and self.nonlinear <= other.nonlinear

    # def __eq__(self, value) -> bool:
    #     if isinstance(value, BoolPoly):
    #         return (
    #             self.const == value.const
    #             and self.linear == value.linear
    #             and self.nonlinear == value.nonlinear
    #         )
    #     if isinstance(value, int):
    #         return self.const == value and not self.linear and not self.nonlinear

    # def __neq__(self, value) -> bool:
    #     if isinstance(value, BoolPoly):
    #         return (
    #             self.const != value.const
    #             or self.linear != value.linear
    #             or self.nonlinear != value.nonlinear
    #         )
    #     if isinstance(value, int):
    #         return self.const != value or not self.linear or not self.nonlinear

    def is_var(self) -> bool:
        return len(self.linear) == 1 and not self.nonlinear

    def is_const(self) -> bool:
        return not self.linear and not self.nonlinear

    def is_zero(self) -> bool:
        return not self.const and self.is_const()

    def is_one(self) -> bool:
        return self.const and self.is_const()

    def __str__(self) -> str:
        str_linear = " + ".join("x" + str(var) for var in self.linear)
        str_nonlinear = " + ".join(
            " * ".join("x" + str(var) for var in mono) for mono in self.nonlinear
        )
        res = []
        if self.const:
            res.append(str(int(self.const)))
        if self.linear:
            res.append(str_linear)
        if self.nonlinear:
            res.append(str_nonlinear)
        return " + ".join(res) or "0"


class BoolPolyLane:
    def __init__(self, lanesize: int, rdc_src: "BoolPolySystem" = None) -> None:
        self.lanesize = lanesize
        self.lane = [BoolPoly(False, set(), set(), rdc_src) for _ in range(lanesize)]
        self.rdc_src = rdc_src

    def __setitem__(self, key: int, value: BoolPoly) -> None:
        if key >= self.lanesize:
            raise IndexError("Index out of range")
        self.lane[key] = value

    def init_var(self, stnum: int) -> None:
        for idx, poly in enumerate(self.lane):
            poly.linear = set([stnum + idx])

    def init_const(self, const: bool) -> None:
        for poly in self.lane:
            poly.const = const

    def __getitem__(self, key: int) -> BoolPoly:
        return self.lane[key]

    def __xor__(self, other: typing.Union["BoolPolyLane", int]) -> "BoolPolyLane":
        res = BoolPolyLane(self.lanesize, self.rdc_src)
        if isinstance(other, BoolPolyLane):
            res.lane = [a ^ b for a, b in zip(self.lane, other.lane)]
        elif isinstance(other, int):
            res.lane = [poly ^ ((other >> i) & 1) for i, poly in enumerate(self.lane)]
        else:
            raise TypeError("Unsupported type for xor operation")
        return res

    def __and__(self, other: "BoolPolyLane") -> "BoolPolyLane":
        res = BoolPolyLane(self.lanesize, self.rdc_src)
        res.lane = [a & b for a, b in zip(self.lane, other.lane)]
        return res

    def __invert__(self) -> "BoolPolyLane":
        res = BoolPolyLane(self.lanesize, self.rdc_src)
        res.lane = [~poly for poly in self.lane]
        return res

    def __lshift__(self, other) -> "BoolPolyLane":
        res = BoolPolyLane(self.lanesize, self.rdc_src)
        lshift = other % self.lanesize
        res.lane = (
            self.lane[self.lanesize - lshift :] + self.lane[: self.lanesize - lshift]
        )
        return res

    def __str__(self) -> str:
        return "\n".join(str(poly) for poly in self.lane)


KECCAK_F_ROUND_COUNT = 24
RHO = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44]  # fmt: skip
PI = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1]  # fmt: skip
RC = [
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
]


class BoolPolyState:
    def __init__(self, lanesize: int, rdc_src: "BoolPolySystem" = None) -> None:
        self.lanesize = lanesize
        self.state = [BoolPolyLane(self.lanesize, rdc_src) for __ in range(25)]

    def __setitem__(self, key: int, value: typing.Union[BoolPolyLane, int]) -> None:
        if key >= 25:
            raise IndexError("Index out of range")
        self.state[key] = value

    def __getitem__(self, key: int) -> BoolPolyLane:
        if key >= 25:
            raise IndexError("Index out of range")
        return self.state[key]

    def theta(self) -> None:
        array = [BoolPolyLane(self.lanesize) for _ in range(5)]
        for x in range(5):
            for y in range(5):
                array[x] ^= self.state[5 * y + x]
        for x in range(5):
            for y in range(5):
                self.state[5 * y + x] ^= array[(x + 4) % 5] ^ (array[(x + 1) % 5] << 1)

    def conditional_theta(self, bps) -> None:
        array = [BoolPolyLane(self.lanesize) for _ in range(5)]
        for x in range(5):
            for y in range(5):
                array[x] ^= self.state[5 * y + x]
        for i in range(5):
            for j in range(array[i].lanesize):
                bps.append(BoolPoly(False, array[i][j].linear, array[i][j].nonlinear))
                array[i][j].linear = set()
                array[i][j].nonlinear = set()
        for x in range(5):
            for y in range(5):
                self.state[5 * y + x] ^= array[(x + 4) % 5] ^ (array[(x + 1) % 5] << 1)

    def rho_pi(self) -> None:
        last = self.state[1]
        for x in range(24):
            temp = self.state[PI[x]]
            self.state[PI[x]] = last << RHO[x]
            last = temp

    def chi(self) -> None:
        from copy import deepcopy

        for y in range(0, 25, 5):
            array = [deepcopy(self.state[y + x]) for x in range(5)]
            for x in range(5):
                self.state[y + x] = array[x] ^ (
                    ~array[(x + 1) % 5] & array[(x + 2) % 5]
                )

    def iota(self, rci) -> None:
        self.state[0] ^= RC[rci]

    def __str__(self) -> str:
        return "\n\n".join(str(lane) for lane in self.state)


class BoolPolySystem:
    def __init__(self) -> None:
        self.polys = []
        self.assignments = {}

    def __str__(self) -> str:
        return "\n".join(str(poly) for poly in self.polys)

    def append(self, p: BoolPoly) -> None:
        if p.is_zero():
            return
        for i, poly in enumerate(self.polys):
            if poly <= p:
                p ^= poly
            if p.is_zero():
                return
            if p <= poly:
                self.polys[i] ^= p
        self.polys.append(p)

    def rdc(self, poly: BoolPoly) -> BoolPoly:
        for p in self.polys:
            if p <= poly:
                poly ^= p
        return poly

    def set_value(self, var: int, value: bool) -> None:
        if var in self.assignments:
            raise ValueError("Variable already assigned")
        self.assignments[var] = value
        for poly in self.polys:
            poly[var] = value

    def clean_zero(self) -> None:
        self.polys = [poly for poly in self.polys if not poly.is_zero()]

    # def simple_simplyfy(self) -> None:
    #     self.polys.sort(key=lambda x: len(x.linear))
    #     new_polys = []
    #     for poly in self.polys:
    #         for new_poly in new_polys:
    #             if new_poly <= poly:
    #                 poly ^= new_poly
    #         if not poly.is_zero():
    #             new_polys.append(poly)
    #     self.polys = new_polys
    #     # self.clean_zero()

    # False: no solution, True: solution found, None: no change
    def simple_propogate(self) -> typing.Union[bool, None]:
        self.clean_zero()
        if not self.polys:
            return True
        new_assignments = {}
        for poly in self.polys:
            if poly.is_one():
                return False
            if poly.is_var():
                new_assignments[list(poly.linear)[0]] = poly.const
        print(new_assignments)
        if new_assignments:
            for var, value in new_assignments.items():
                self.set_value(var, value)
            return self.simple_propogate()
        else:
            return None


class BoolLinear:
    def __init__(self, const: bool, linear) -> None:
        self.const = bool(const)
        self.linear = deepcopy(linear)

    def __xor__(self, other: "BoolLinear") -> "BoolLinear":
        return BoolLinear(self.const ^ other.const, self.linear ^ other.linear)

    def __contains__(self, var: int) -> bool:
        return var in self.linear

    def is_const(self) -> bool:
        return not self.linear

    def choose_var(self) -> int:
        return list(self.linear)[0]

    def __str__(self) -> str:
        return f"{int(self.const)} + {' + '.join(f'x{var}' for var in self.linear)}"


class BoolLinearSolver:
    def __init__(self, bps: BoolPolySystem) -> None:
        for poly in bps.polys:
            if poly.nonlinear:
                raise ValueError("Only support linear equations")
        self.eqs = [BoolLinear(poly.const, poly.linear) for poly in bps.polys]
        self.pivot_eq = {}
        self.assignments = deepcopy(bps.assignments)

    def solve(self):
        for i in range(len(self.eqs)):
            if self.eqs[i].is_const():
                if self.eqs[i].const:
                    return False
                continue
            var = self.eqs[i].choose_var()
            self.pivot_eq[var] = i
            for j in range(len(self.eqs)):
                if i == j:
                    continue
                if var in self.eqs[j]:
                    self.eqs[j] ^= self.eqs[i]
        for var, eq_idx in self.pivot_eq.items():
            self.assignments[var] = int(self.eqs[eq_idx].const)
            for i in self.eqs[eq_idx].linear:
                if i != var and i not in self.assignments.keys():
                    self.assignments[i] = 0
        return self.assignments
