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

    def removeClusterMember(self, supplier):
        self.clusterMembers.remove(supplier)

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

    def getPriority(self):
        """
        get the priority of the supplier
        """
        priority = 0
        priority += len(self.aroundSuppliers) # tend to choose the supplier with more around suppliers
        priority += len(self.aroundRiders) # tend to choose the supplier with more around riders
        # priority -= self.distanceToOrder # tend to choose the supplier with the shortest distance to order
        # priority -= self.getNearestRiderDistance() # tend to choose the supplier with the shortest distance to nearest rider
        priority += len(self.items) + sum(self.items.values()) # tend to choose the supplier with more items
        return priority

    def isClusterCenter(self):
        return self.isClustered() and self.clusterCenter.id == self.id

    def isClustered(self):
        return self.clusterCenter != None

    def __str__(self) -> str:
        return "Supplier {}, Cluster {}, Items {}, aroundSupplier {}, aroundRiders {}".format(self.id, self.clusterCenter.id if self.isClustered() else "None" , self.items, [supplier.id for supplier in self.aroundSuppliers], [rider.id for rider, distance in self.aroundRiders])

    def __repr__(self) -> str:
        return "Supplier {}, Cluster {}, Items {}, aroundSupplier {}, aroundRiders {}".format(self.id, self.clusterCenter.id if self.isClustered() else "None" , self.items, [supplier.id for supplier in self.aroundSuppliers], [rider.id for rider, distance in self.aroundRiders])



class Rider:
    def __init__(self, id:int):
        self.id = id
        self.nearestSupplier = None

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

class Route:
    def __init__(self, order:Order):

        self.rider = None
        self.suppliers = []
        self.num_suppliers = 0
        self.order = order
        self.totalItems = {}
        self.itemsForEachSupplier = {}
        self.cost = float("inf")

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
            response.deliverer_id = self.rider.id
        for supplier in self.suppliers[:self.num_suppliers]:
            tmp_itemlist = ItemList_pb2(items=self.itemsForEachSupplier[supplier.id])
            tmp_route = Route_pb2(supplier_id=supplier.id, itemlist=tmp_itemlist)
            response.route.append(tmp_route)
        return response

    def setCost(self, cost:float):
        self.cost = cost

    def __str__(self) -> str:
        return "Route: Rider {}, Order {}, NumSuppliers {}, TotalItems {}, Suppliers {}".format(self.rider.id, (self.order.id,self.order.items), self.num_suppliers, self.totalItems, [itemlist for itemlist in self.itemsForEachSupplier.items()])

    def __repr__(self) -> str:
        return "Route: Rider {}, Order {}, NumSuppliers {}, TotalItems {}, Suppliers {}".format(self.rider.id, (self.order.id,self.order.items), self.num_suppliers, self.totalItems, [itemlist for itemlist in self.itemsForEachSupplier.items()])


