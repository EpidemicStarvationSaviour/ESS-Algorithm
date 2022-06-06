import numpy as np
from typing import List, Tuple
import random

from .role import Supplier, Rider, Order, Route

class RouteScheduler:

    def __init__(self, aroundScope:float = 100.0, maxIteration:int = 100):
        self.aroundScope = aroundScope
        self.maxIteration = maxIteration
        self.clusters = []

    def initializeFromRequest(self, request):
        """
        Brief:
            initialize the request from the request object
        """
        self.clusters = []
        self.order = Order(0, dict(request.request.items))
        self.suppliers = [Supplier(index + 1, dict(item.items)) for index, item in enumerate(list(request.itemlists))]
        self.numRider = request.num_deliverer
        self.riders = [Rider(index + len(self.suppliers) + 1, index + 1) for index in range(self.numRider)]
        self.distances = list(request.distance)

        dict_suppliers = {}
        for supplier in self.suppliers:
            dict_suppliers[supplier.id] = supplier
        self.suppliers = dict_suppliers

        dict_riders = {}
        for rider in self.riders:
            dict_riders[rider.id] = rider
        self.riders = dict_riders


        for supplier1 in self.suppliers.values():
            supplier1.setAroundScope(self.aroundScope)
            supplier1.setDistanceToOrder(self.getDistance(supplier1.id, self.order.id))
            # cluster suppliers
            for supplier2 in self.suppliers.values():
                if supplier1.id == supplier2.id:
                    continue
                if self.getDistance(supplier1.id, supplier2.id) <= self.aroundScope:
                    supplier1.addAroundSupplier(supplier2)
        # # set the nearest rider around each supplier

        for rider in self.riders.values():
            nearestSupplier = None
            nearestDistance = float('inf')

            for supplier in self.suppliers.values():

                if nearestSupplier == None:
                    nearestSupplier = supplier
                    nearestDistance = self.getDistance(rider.id, supplier.id)
                else:
                    if self.getDistance(rider.id, supplier.id) < nearestDistance:
                        nearestSupplier = supplier
                        nearestDistance = self.getDistance(rider.id, supplier.id)
            rider.setNearestSupplier(nearestSupplier, nearestDistance)
            nearestSupplier.addAroundRider(rider, nearestDistance)

        for supplier in self.suppliers.values():
            if len(supplier.aroundRiders) == 0:
                nearestRider = None
                nearestDistance = float('inf')
                for rider in self.riders.values():
                    if nearestRider == None:
                        nearestRider = rider
                        nearestDistance = self.getDistance(supplier.id, rider.id)
                    else:
                        if self.getDistance(supplier.id, rider.id) <= nearestDistance:
                            nearestRider = rider
                            nearestDistance = self.getDistance(supplier.id, rider.id)
                supplier.addAroundRider(nearestRider, nearestDistance)

        self.clusterSuppliers()

    def scheduleRoute(self,request):
        """
        Brief:
            Schedule a route for the given request.
        Args:
            request: pg2 request object
        Returns:
            response (scheduleReply) : the generated schedule route reply result
        """
        # read the request
        self.initializeFromRequest(request)

        initialRoute = self.greedyInitialization()
        # if all of the current suppliers can't satisfy the order, return a empty schedule
        # print(initialRoute) # debug
        if not initialRoute.isEnoughSuppliers():
            return Route(self.order).generateResponse()
        self.best_route = initialRoute

        # for supplier in self.suppliers.values(): # debug
        #     print(supplier) # debug
        # do local search
        self.localSearch()

        return self.best_route.generateResponse()

    def greedyInitialization(self):
        """
        Brief:
            Compute the initial route schedule with greedy insertion
        Return:
            route (Route) : the initial route computed by greedy insertion
        """

        # initialize the supplier rank

        self.clusters = sorted(self.clusters, key=lambda x: x.getClusterPriority(self.order.items), reverse=True)
        rankedSuppliers = []
        for cluster in self.clusters:
            cluster.clusterMembers = sorted(cluster.clusterMembers, key=lambda x: x.getPriority(self.order.items), reverse=True)
            rankedSuppliers.extend(cluster.clusterMembers)
        # # initialize the route
        route = Route(self.order)
        route.setRider(rankedSuppliers[0].getNearestRider())
        # # initialize the route with greedy insertion
        for supplier in rankedSuppliers:
            route.addSupplier(supplier)
        route.setCost(self.EvaluateRoute(route))
        return route


    def getLocalCluster(self):
        """
        Brief:
            do local search for the current clusters rank, generate a new clusters rank and return
        """
        clusters = self.clusters.copy()
        # random.shuffle(clusters)
        # return clusters
        # find the cluster that need to be swapped
        if random.random() < 0.5:
            cluster1 = random.choice(clusters[:len(self.best_route.numSupplierEachCluster)])
            if random.random() < 0.5:
                cluster2 = random.choice(clusters[:len(self.best_route.numSupplierEachCluster)])
            else:
                cluster2 = random.choice(clusters[len(self.best_route.numSupplierEachCluster)-1:])
            # swap the cluster
            index1 = clusters.index(cluster1)
            index2 = clusters.index(cluster2)
            clusters[index1], clusters[index2] = clusters[index2], clusters[index1]
        else:
            # if the current Supplier
            cluster = random.choice(clusters[:len(self.best_route.numSupplierEachCluster)])
            if random.random() < 0.1:
                cluster.clusterMembers = sorted(cluster.clusterMembers, key=lambda x: x.getPriority(self.order.items), reverse=True)
            else:
                random.shuffle(cluster.clusterMembers)
        return clusters

    def localSearch(self):
        """
        Brief:
            Local search for the given route.
        Args:

        Return:

        """
        for _ in range(self.maxIteration):
            clusters = self.getLocalCluster()
            rankedSuppliers = []
            for cluster in clusters:
                rankedSuppliers.extend(cluster.clusterMembers)
            # initialize the route
            route = Route(self.order)
            route.setRider(rankedSuppliers[0].getNearestRider())
            # initialize the route with greedy insertion
            for supplier in rankedSuppliers:
                route.addSupplier(supplier)
            route.setCost(self.EvaluateRoute(route))
            if route.cost < self.best_route.cost:
                # print("- New best route found") # debug
                # print(route) # debug
                self.best_route = route
                self.clusters = clusters


    def getDistance(self, id1:int, id2:int):
        """
        Brief:
            return distance between two units
        Args:
            id1: id of first unit
            id2: id of second unit
        Returns:
            distance between two units
        """
        if id1 > id2:
            id1, id2 = id2, id1
        n = len(self.suppliers)
        m = len(self.suppliers) + self.numRider
        assert id1 >= 0 and id2 >= 0, "id1 and id2 must be non-negative"
        assert id1 <= len(self.suppliers), "Invalid order or supplier id"
        assert id2 <= len(self.suppliers) + self.numRider, "Invalid order or supplier id or rider id"
        assert id2 <= len(self.suppliers) if id1 == 0 else True, "Distances involving order address should only be compared with suppliers"
        if id1 == id2:
            return 0
        if id1 == 0:
            return self.distances[id2 - 1]
        else:
            index = n
            num_series = id1 - 1
            index += num_series * (m - 1) - num_series * (num_series - 1) // 2
            index += id2 - id1 - 1
            return self.distances[index]

    def EvaluateRoute(self, route:Route):
        """
        Evaluate the given route.
        """
        total_cost = 0
        if len(route.suppliers) != 0:
            total_cost += self.getDistance(route.rider.id, route.suppliers[0].id)
            for i in range(len(route.suppliers)-1):
                total_cost += self.getDistance(route.suppliers[i].id, route.suppliers[i+1].id)
            total_cost += self.getDistance(route.suppliers[-1].id, route.order.id)
        else:
            total_cost = float('inf')
        return total_cost

    def clusterSuppliers(self):
        """
        Cluster suppliers into clusters.
        """
        # cluster suppliers
        clusterIds = list(self.suppliers.keys())
        clusterIds = sorted(clusterIds, key=lambda x: len(self.suppliers[x].aroundSuppliers), reverse=True)
        while len(clusterIds) > 0:
            clusterCenter = self.suppliers[clusterIds[0]]
            clusterIds.remove(clusterIds[0])
            clusterCenter.setCenter()
            self.clusters.append(clusterCenter)
            for supplier in clusterCenter.aroundSuppliers:
                supplier.updateClusterIfCloser(clusterCenter, self.getDistance(supplier.id, clusterCenter.id))
                if supplier.id in clusterIds:
                    clusterIds.remove(supplier.id)





