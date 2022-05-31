import os, sys
import traceback
sys.path.insert(0, os.path.abspath("./ESS_Protobuf"))

from concurrent import futures
import time
import grpc
from ESS_Protobuf.interface_pb2 import (
    ItemList,
    Route,
    ScheduleReply,
    PingReply
)
import ESS_Protobuf.interface_pb2_grpc as interface_pb2_grpc
import DVPR

scheduler = DVPR.RouteScheduler() # new scheduler

class Algorithm(interface_pb2_grpc.AlgorithmServicer):
    def Ping(self, request, context):
        print("Received: " + request.message)
        return PingReply(message = 'Pong')
    def Schedule(self, request, context):
        try:
            response = scheduler.scheduleRoute(request)
        except Exception as e:
            traceback.print_exc()
        print(response) # debug
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
