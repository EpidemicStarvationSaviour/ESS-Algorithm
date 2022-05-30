from pydoc import resolve
from turtle import distance
import numpy as np
from typing import List, Tuple
import random
from interface_pb2 import (
    ItemList as ItemList_pb2,
    Route as Route_pb2,
    ScheduleReply as ScheduleReply_pb2,
)

class Supplier:
    def __init__(self, id:int, items:dict = None):
        self.id = id
        self.items = items if items is not None else {}
        self.clusterCenter = None
        self.distanceToClusterCenter = float("inf")
        self.clusterMembers = []
        self.aroundSuppliers = []
        self.aroundRiders = []
        self.aroundScope = 0
        self.clusterItems = {}
        for item in list(self.items.keys()):
            if self.items[item] <= 0.0:
                del self.items[item]
        self.priority = None

    def addItem(self, item:str, amount:float):
        self.items[item] = amount

    def setCenter(self):
        self.clusterCenter = self
        self.distanceToClusterCenter = 0
        self.addClusterMember(self)

    def setCluster(self, cluster, distance:float):
        self.clusterCenter = cluster # the center supplier id of the cluster
        self.distanceToClusterCenter = distance # the distance to the center supplier
        cluster.addClusterMember(self)

    def addClusterMember(self, supplier):
        self.clusterMembers.append(supplier)
        for item in supplier.items:
            self.clusterItems[item] = self.clusterItems.get(item, 0) + supplier.items[item]

    def removeClusterMember(self, supplier):
        self.clusterMembers.remove(supplier)
        for item in supplier.items:
            self.clusterItems[item] = self.clusterItems.get(item, 0) - supplier.items[item]

    def updateClusterIfCloser(self, cluster, distance:float):
        """
        update the cluster center to new cluster if the distance is smaller
        """
        if self.distanceToClusterCenter > distance:
            if self.clusterCenter is not None:
                self.clusterCenter.removeClusterMember(self)
            self.setCluster(cluster, distance)

    def setAroundScope(self, scope:float):
        """
        set the scope of the around supplier
        """
        self.aroundScope = scope


    def setDistanceToOrder(self, distance:float):
        self.distanceToOrder = distance

    def addAroundSupplier(self, supplier):
        """
        add around supplier
        """
        self.aroundSuppliers.append(supplier)

    def addAroundRider(self, rider, distance:float):
        """
        add around rider id
        """
        self.aroundRiders.append((rider, distance))

    def getNearestRider(self):
        """
        get the nearest rider
        """
        if len(self.aroundRiders) == 0:
            return None
        return min(self.aroundRiders, key=lambda x: x[1])[0]

    def getNearestRiderDistance(self):
        """
        get the nearest rider
        """
        if len(self.aroundRiders) == 0:
            return None
        return min(self.aroundRiders, key=lambda x: x[1])[1]

    def getClusterPriority(self, requestItems:dict, alpha:float = 0.1) -> float:
        """
        get the priority of the supplier
        Args:
            requestItems: the items that the rider wants to buy
            alpha: the bigger alpha, the more prosperous cluster will be preferred
        """
        if not self.isClusterCenter():
            if not self.isClustered():
                return self.getPriority(requestItems)
            else:
                return self.clusterCenter.getClusterPriority(requestItems)
        priority = 0
        priority -= self.distanceToOrder # tend to choose the supplier with the shortest distance to order
        priority -= self.getNearestRiderDistance() # tend to choose the supplier with the shortest distance to nearest rider
        priority *= (1 + alpha*np.exp(-len(self.aroundRiders) - len(self.aroundSuppliers))) # tend to choose the supplier with more around suppliers and riders
        priority *= np.sum((1 + alpha*np.exp(-np.array([self.clusterItems[item] for item in requestItems.keys() if item in self.clusterItems])))) # tend to choose the supplier with more items
        if self.isClusterCenter():
            self.priority = priority
        return priority

    def getPriority(self, requestItems:dict, alpha:float = 0.1) -> float:
        """
        get the priority of the supplier
        Args:
            requestItems: the items that the rider wants to buy
            alpha: the bigger alpha, the more prosperous supplier will be preferred
        """
        priority = 0
        priority -= self.distanceToOrder # tend to choose the supplier with the shortest distance to order
        priority -= self.getNearestRiderDistance() # tend to choose the supplier with the shortest distance to nearest rider
        priority *= (1 + alpha*np.exp(-len(self.aroundRiders) - len(self.aroundSuppliers))) # tend to choose the supplier with more around suppliers and riders
        priority *= np.sum((1 + alpha*np.exp(-np.array([self.items[item] for item in requestItems.keys() if item in self.items])))) # tend to choose the supplier with more items
        if not self.isClusterCenter():
            self.priority = priority
        return priority

    def isClusterCenter(self):
        return self.isClustered() and self.clusterCenter.id == self.id

    def isClustered(self):
        return self.clusterCenter != None

    def __str__(self) -> str:
        return "Supplier {}, Cluster {}, Items {}, AroundSupplier {}, AroundRiders {}, DistanceToOrder {}, DistanceToNearestRider {}, Priority {}".format(
            self.id,
            self.clusterCenter.id if self.isClustered() else "None",
            self.items, [supplier.id for supplier in self.aroundSuppliers],
            [rider.id for rider, distance in self.aroundRiders],
            self.distanceToOrder,
            self.getNearestRiderDistance(),
            self.priority
            )

    def __repr__(self) -> str:
        return "Supplier {}, Cluster {}, Items {}, AroundSupplier {}, AroundRiders {}, DistanceToOrder {}, DistanceToNearestRider {}, Priority {}".format(
            self.id,
            self.clusterCenter.id if self.isClustered() else "None",
            self.items, [supplier.id for supplier in self.aroundSuppliers],
            [rider.id for rider, distance in self.aroundRiders],
            self.distanceToOrder,
            self.getNearestRiderDistance(),
            self.priority
            )

    def __eq__(self, other:object):
        if other is None:
            return False
        return self.id == other.id



class Rider:
    def __init__(self, id:int, responseId:int):
        self.id = id
        self.nearestSupplier = None
        self.responseId = responseId

    def setNearestSupplier(self, supplier:Supplier, distance:float):
        self.nearestSupplier = supplier
        self.distanceToNearestSupplier = distance

    def __str__(self) -> str:
        return "Rider {}, Nearest Supplier {}".format(self.id, self.nearestSupplier.id if self.nearestSupplier is not None else "None")

    def __repr__(self) -> str:
        return "Rider {}, Nearest Supplier {}".format(self.id, self.nearestSupplier.id if self.nearestSupplier is not None else "None")

class Order:
    def __init__(self, id:int, items:dict = None):
        self.id = id
        self.items = items if items is not None else {}
        for item in list(self.items.keys()):
            if self.items[item] <= 0.0:
                del self.items[item]

class Route:
    def __init__(self, order:Order):

        self.rider = None
        self.suppliers = []
        self.num_suppliers = 0
        self.order = order
        self.totalItems = {}
        self.itemsForEachSupplier = {}
        self.cost = float("inf")
        self.numSupplierEachCluster = {}

    def setRider(self, rider:Rider):
        self.rider = rider

    def addSupplier(self, supplier:Supplier):
        """
        Brief:
            add supplier for this route
        Args:
            supplier: the supplier to be added
        Return:
            (bool) : True if the supplier is added, False if not
        """
        itemlist = {}
        if self.isEnoughSuppliers():
            return False
        for item in self.order.items:
            self.totalItems[item] = self.totalItems.get(item, 0)
            if self.totalItems[item] > self.order.items[item]:
                itemlist[item] = 0
            else:
                if self.totalItems[item] + supplier.items.get(item, 0) > self.order.items[item]:
                    itemlist[item] = self.order.items[item] - self.totalItems[item]
                else:
                    itemlist[item] = supplier.items.get(item, 0)
            self.totalItems[item] += supplier.items.get(item, 0)

        if sum(itemlist.values()) > 0:
            self.itemsForEachSupplier[supplier.id] = itemlist
            self.suppliers.append(supplier)
            self.numSupplierEachCluster[supplier.clusterCenter.id] = self.numSupplierEachCluster.get(supplier.clusterCenter.id, 0) + 1
            self.num_suppliers += 1
            return True

    def isEnoughSuppliers(self):
        for item in self.order.items:
            if self.totalItems.get(item, 0) < self.order.items[item]:
                return False
        return True

    def generateResponse(self):
        response = ScheduleReply_pb2()
        if self.rider is not None:
            response.deliverer_id = self.rider.responseId
        for supplier in self.suppliers[:self.num_suppliers]:
            tmp_itemlist = ItemList_pb2(items=self.itemsForEachSupplier[supplier.id])
            tmp_route = Route_pb2(supplier_id=supplier.id, itemlist=tmp_itemlist)
            response.route.append(tmp_route)
        return response

    def setCost(self, cost:float):
        self.cost = cost

    def __str__(self) -> str:
        return "Route: Rider {}, Order {}, NumSuppliers {}, TotalItems {}, Suppliers {}, Cost {}".format(
            self.rider.id if self.rider is not None else "None",
            (self.order.id,self.order.items),
            self.num_suppliers, self.totalItems,
            [itemlist for itemlist in self.itemsForEachSupplier.items()],
            self.cost,
            )

    def __repr__(self) -> str:
        return "Route: Rider {}, Order {}, NumSuppliers {}, TotalItems {}, Suppliers {}, Cost {}".format(
            self.rider.id if self.rider is not None else "None",
            (self.order.id,self.order.items),
            self.num_suppliers, self.totalItems,
            [itemlist for itemlist in self.itemsForEachSupplier.items()],
            self.cost,
            )

