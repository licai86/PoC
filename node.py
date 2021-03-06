from __future__ import print_function

import time
import socket
import subprocess
import argparse
import uuid

import tornado.web
# import tornado.websocket
import tornado.ioloop
import tornado.options
import tornado.httpserver
# import tornado.httpclient
import tornado.gen
import tornado.escape

import setting
import tree
import miner
import leader
import database
import fs

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/node", tree.NodeHandler),
                    (r"/buddy", tree.BuddyHandler),
                    (r"/leader", leader.LeaderHandler),
                    (r"/available_branches", AvailableBranchesHandler),
                    (r"/get_group", GetGroupHandler),
                    (r"/disconnect", DisconnectHandler),
                    (r"/broadcast", BroadcastHandler),
                    (r"/new_tx", NewTxHandler),
                    (r"/dashboard", DashboardHandler),
                    # mtfs
                    (r"/user", fs.UserHandler),
                    (r"/object", fs.ObjectHandler),
                    (r"/capsule", fs.CapsuleHandler),
                    ]
        settings = {"debug":True}

        tornado.web.Application.__init__(self, handlers, **settings)


class AvailableBranchesHandler(tornado.web.RequestHandler):
    def get(self):
        branches = list(tree.available_branches)

        # parents = []
        # for node in tree.NodeConnector.parent_nodes:
        #     parents.append([node.host, node.port])
        self.finish({"available_branches": branches,
                     "buddy":len(tree.available_buddies),
                     #"parents": parents,
                     "groupid": tree.current_groupid})

class GetGroupHandler(tornado.web.RequestHandler):
    def get(self):
        groupid = self.get_argument("groupid")
        target_groupid = groupid
        score = None
        # print(tree.current_port, tree.node_neighborhoods)
        for j in [tree.node_neighborhoods, tree.node_parents]:
            for i in j:
                new_score = tree.group_distance(groupid, i)
                if score is None or new_score < score:
                    score = new_score
                    target_groupid = i
                    address = j[target_groupid]
                # print(i, new_score)

        self.finish({"address": address,
                     "groupid": target_groupid,
                     "current_groupid": tree.current_groupid})

class DisconnectHandler(tornado.web.RequestHandler):
    def get(self):
        while tree.NodeConnector.parent_nodes:
            # connector.remove_node = False
            tree.NodeConnector.parent_nodes.pop().close()

        while tree.BuddyConnector.buddy_nodes:
            # connector.remove_node = False
            tree.BuddyConnector.buddy_nodes.pop().close()

        self.finish({})
        tornado.ioloop.IOLoop.instance().stop()

class BroadcastHandler(tornado.web.RequestHandler):
    def get(self):
        test_msg = ["TEST_MSG", tree.current_groupid, time.time(), uuid.uuid4().hex]

        tree.forward(test_msg)
        self.finish({"test_msg": test_msg})

class NewTxHandler(tornado.web.RequestHandler):
    def post(self):
        tx = tornado.escape.json_decode(self.request.body)

        tree.forward(["NEW_TX", tx, time.time(), uuid.uuid4().hex])
        self.finish({"txid": tx["transaction"]["txid"]})

class DashboardHandler(tornado.web.RequestHandler):
    def get(self):
        branches = list(tree.available_branches)
        branches.sort(key=lambda l:len(l[2]))

        parents = []
        self.write("<br>current_groupid: %s <br>" % tree.current_groupid)
        self.write("<br>available_branches:<br>")
        for branch in branches:
            self.write("%s %s %s <br>" %branch)

        self.write("<br>available_buddies: %s<br>" % len(tree.available_buddies))
        for buddy in tree.available_buddies:
            self.write("%s %s <br>" % buddy)

        self.write("<br>parent_nodes:<br>")
        for node in tree.NodeConnector.parent_nodes:
            self.write("%s %s<br>" %(node.host, node.port))

        self.write("<br>available_children_buddies:<br>")
        for k,vs in tree.available_children_buddies.items():
            self.write("%s<br>" % k)
            for v1,v2 in vs:
                self.write("%s %s<br>" % (v1,v2))

        self.write("<br>LeaderHandler:<br>")
        for node in leader.LeaderHandler.leader_nodes:
            self.write("%s %s<br>" %(node.from_host, node.from_port))

        self.write("<br>LeaderConnector:<br>")
        for node in leader.LeaderConnector.leader_nodes:
            self.write("%s %s<br>" %(node.host, node.port))

        self.write("<br>node_parents:<br>")
        for groupid in tree.node_parents:
            host, port = tree.node_parents[groupid][0]
            self.write("%s:%s %s<br>" %(groupid, host, port))

        self.write("<br>node_neighborhoods:<br>")
        for groupid in tree.node_neighborhoods:
            host, port = tree.node_neighborhoods[groupid][0]
            self.write("%s:%s %s<br>" %(groupid, host, port))

        self.finish()

def main():
    tree.main()
    database.main()
    # fs.main()
    tornado.ioloop.IOLoop.instance().call_later(20, miner.main)

    server = Application()
    server.listen(tree.current_port)
    tornado.ioloop.IOLoop.instance().add_callback(tree.connect)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
