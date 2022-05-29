# DVRP(Dynamic Vehicle Routing Problem)

This is the 2022 ZJU Software Engineering algorithm side.

## 1 Problem Background

### 问题描述

我们针对疫情管制下社区团购的背景进行研究。在过去一段时间(1分钟)内产生了一些社区团购订单。每个订单都将由一个骑手接单，多个商家供货，一个地址收货。模型根据当前时间空余骑手、商家和收获地址之间的位置，规划本订单接单的骑手，接单骑手的收送货路径和预计送达时间。

### 问题约束

- **一骑一单**：每个骑手每次最多接一个团购订单，完成本次订单后方可接下一单
- **订单信息**：每个团购订单提供所需货物与收获地址信息。收货地址信息仅有一个
- **供货约定**：每个商家可以商家指定数量的多种货物
- **合作供货**：单次订单允许多个商家共同供货，共同供货方案有模型给出
- **超级骑手**：我们不考虑骑手本身的送货容量限制

## 2 Problem Formulation

### 2.1 符号约定

- 位置集合$P$
- 货品集合$B=\{(k,c)|k,c\in\mathbb{R}\}$,$k$表示货品种类，$c$表示该类货品数量
- 骑手集合$R=\{(p_i,f_i)|p_i \in P, f_i\in \{0,1\}\}$，$p_i$表示$i$个骑手位置，$f_i$表示第i个骑手是否空闲
- 商家集合$M=\{(p_i,b_i)|p_i\in P, b_i\sub B\}$,$b_i$为商家上架的所有货品集合
- 订单集合$O=\{(p_i,b_i)|p_i \in P, b_i \sub B\}$,$b_i$为订单需要的的所有货品集合
- 取货边集$E_f=\{(r_i,m_j)|r_i\in R, m_j \in M\}$
- 送货边集$E_s=\{(m_i,o_j)|m_i \in M, o_j \in O\}$
- 代价集合$C=\{c_e|e\in E_f\cup E_s\}$，可以使用函数$c(r_i,m_j)$表示骑手$r_i$到商家$m_j$的距离，$c(m_i,o_j)$表示商家$m_i$到订单收货地址$o_j$的距离，
- 合作供货序列$s=\{(m_i,b_i)|m_i\in M, b_i \in B\}$，$S$为所有该有序序列的集合。其中$m_i$表示商家，$b_i$表示该商家为本次订单供给的货品集合。可以使用$c(S)=\sum^{}_{i=1}c(m_i,b_i)$表示依次遍历这些商家所需要的的代价
### 2.2 单次订单优化目标

$$
min \c(r,m_1)+c(s_i)+c(m_n,o)\\
s.t. r\in R,\ o\in O\\
s_i=\{(m_1,b_1), ..., (m_n,b_n)\},\\

$$
## 3 Algorith Design

### 3.1 Problem Analysis

本问题主要包括两个子问题，
- 根据订单需求分配供货商
- 根据已经确定的供货商进行路径规划

两个问题在优化目标的约束下互相牵制，单独解每一个问题都得不到全局最优解。其中路径规划是NP-hard问题。所以，我们完全可以放弃考虑精确算法，转而采用近似算法(approximation algorithm)，或者是启发式算法(heuristic algorithm)

### 3.2 算法设计思路

问题可以简单描述为，单个骑手通过多个固定供货商到达指定送货点的最短路径规划问题。对问题中的我们不考虑供货商货物的均衡分配，因此我们在算法中趋向于贪婪分配。

#### 供应商聚类


#### 贪婪插入初始化

#### 局部搜索最优化


## 4 Install Module

安装DVPR包
```bash
pip install -e .
```
在protobuf模块中使用
```python
from concurrent import futures
import time
import grpc
from interface_pb2 import (
    ItemList,
    Route,
    ScheduleReply,
    PingReply
)
import interface_pb2_grpc
import DVPR

scheduler = DVPR.RouteScheduler() # new scheduler

class Algorithm(interface_pb2_grpc.AlgorithmServicer):
    def Ping(self, request, context):
        print("Received: " + request.message)
        return PingReply(message = 'Pong')
    def Schedule(self, request, context):
        response = scheduler.scheduleRoute(request)
        return response

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    interface_pb2_grpc.add_AlgorithmServicer_to_server(Algorithm(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    try:
        while True:
            time.sleep(60*60*24)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()

```
