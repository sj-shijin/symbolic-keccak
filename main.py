from bpkeccak import *


def init_state(x):
    for i in range(5):
        stnum = i * x.lanesize  # 0, 64, 128, 192, 256
        x[i].init_var(stnum)  # 第0行
        # x[i + 5].init_const(1)  # 第1行
        x[i + 10].init_var(stnum)  # 第2行


if __name__ == "__main__":
    x = BoolPolyState(64)  # 25 * 64 bits = 1600 bits
    init_state(x)  # 初始化状态
    bps = BoolPolySystem()  # 用于存储约束

    # 第1轮
    x.theta()  # theta函数
    x.rho_pi()  # rho_pi函数
    x.chi()  # chi函数
    x.iota(0)  # iota函数
    # 第2轮
    x.conditional_theta(bps)  # theta函数
    x.rho_pi()  # rho_pi函数
    x.chi()  # chi函数
    x.iota(1)  # iota函数

    # print(x) # 查看状态
    # print(bps)  # 查看约束

    # 状态前80位为0加入约束
    for cnt in range(80):
        lanenum, bitnum = cnt // x.lanesize, cnt % x.lanesize
        bps.append(x[lanenum][bitnum])

    # 设置消息初始字段
    ID = 0x202318018670057  # 64-bit ID
    init_message = {
        (63 - key): int(val) for key, val in enumerate(bin(ID)[2:].zfill(64))
    }
    for key, val in init_message.items():
        bps.set_value(key, val)

    # 线性化
    linearization = {key: 0 for key in range(272, 288)}
    for key, val in linearization.items():
        bps.set_value(key, val)

    # 求解线性方程组
    solver = BoolLinearSolver(bps)
    sol = solver.solve()

    # 还原初始状态
    message = [0] * 25
    for i in range(5):
        stnum = i * x.lanesize  # 0, 64, 128, 192, 256
        for j in range(x.lanesize):
            message[i] ^= sol[stnum + j] << j
        message[i + 10] = message[i]
    print([hex(m) for m in message])

    # 检验结果
    y = BoolPolyState(64)
    for i in range(25):
        y[i] ^= message[i]
    # 第1轮
    y.theta()  # theta函数
    y.rho_pi()  # rho_pi函数
    y.chi()  # chi函数
    y.iota(0)  # iota函数
    # 第2轮
    y.conditional_theta(bps)  # theta函数
    y.rho_pi()  # rho_pi函数
    y.chi()  # chi函数
    y.iota(1)  # iota函数
    print(y)  # 查看状态
