"""
Read graphs in Open Street Maps osm format

Based on osm.py from brianw's osmgeocode
http://github.com/brianw/osmgeocode, which is based on osm.py from
comes from Graphserver:
http://github.com/bmander/graphserver/tree/master and is copyright (c)
2007, Brandon Martin-Anderson under the BSD License
"""


import xml.sax
import copy
import networkx

import sys
import getopt

import matplotlib.pyplot as plt

import math

def download_osm(left,bottom,right,top):
    """ Return a filehandle to the downloaded data."""
    from urllib import urlopen
    bbox = "%f,%f,%f,%f"%(left,bottom,right,top)
    url = "http://api.openstreetmap.org/api/0.6/map?bbox=" + bbox
    print url
    
    #url = "data.osm"
    url = "graph_in_OSM.osm"
    fp = urlopen( url )
    #fp = urlopen('http://overpass-api.de/api/interpreter?data=%28nodes%28' + bbox + '%29%3B%3C%3B%29%3Bout%20body%3B%0A' )
    return fp

def read_osm(filename_or_stream, only_roads=True):
    """Read graph in OSM format from file specified by name or by stream object.

    Parameters
    ----------
    filename_or_stream : filename or stream object

    Returns
    -------
    G : Graph

    Examples
    --------
    >>> G=nx.read_osm(nx.download_osm(-122.33,47.60,-122.31,47.61))
    >>> plot([G.node[n]['data'].lat for n in G], [G.node[n]['data'].lon for n in G], ',')

    """
    osm = OSM(filename_or_stream)
    G = networkx.Graph()

    for w in osm.ways.itervalues():
        if only_roads and 'highway' not in w.tags:
            continue
        #G.add_path(w.nds, id=w.id, data=w) #problematic becase of to big graph
        #G.add_edge(w.nds[0],w.nds[-1])
        G.add_weighted_edges_from([(w.nds[0],w.nds[-1],osm.calclength(w))])
    for n_id in G.nodes_iter():
        n = osm.nodes[n_id]
        G.node[n_id] = dict(data=n)

    osm.convert2mat()
    return G
        
    
class Edge:
    def __init__(self, eid, wayid, nds, tags, length):
        self.orgid = wayid
        self.id = eid
        self.dest = nds[-1]
        if "name" in tags:
            self.name = tags["name"]
        else:
            self.name = "no name"

        self.length = length

        #TODO parse highway and set self.highway to a number
        hw={'footway':1, 'cycleway':2, 'path':1, 'residental':4,'motorway':3,'trunk':3,'motorway_link':3,'primary':3,
                'secondary':3, 'tertiary':4, 'living_street':4, 'unclassified':4, 'service':4, 'track':2, 'steps':1,
                'bus':5, 'tram':6}
        if "highway" in tags and tags["highway"] in hw:
            self.highway = hw[tags["highway"]]
        else:
            self.highway = "footway"

        self.access_foot = 1
        if "foot" in tags and tags[foot] == "no":
            self.access_foot = 0
        self.access_bike = 1
        if "bicycle" in tags and tags[bicycle] == "no":
            self.access_bike = 0

    def toString(self):
        return "" + str(self.dest) + ", " + self.name + ", " + str(self.length) + ", " + str(self.highway) + ", " + str(self.access_foot) + ", " + str(self.access_bike) + ";"

class Vertex:
    def __init__(self, id, lon, lat, eds, tags):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.eds = []
        self.tags = {}

    def add_edge(self, edge):
        self.eds.append(edge)

    def toString(self):
        name = "no name"
        if "name" in self.tags:
            name = self.tags[name]
#self.eds +
        #tempe =  ["0" for i in range(10-len(self.eds))]
        tempe = [str(i) for i in self.eds] + ["0"]*(10 - len(self.eds))
        edges = ", ".join(tempe)
        return str(self.id)+")\t" + name + ", " + edges + ", " + str(self.lon) + ", " + str(self.lat) + ";"


class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}
        
class Way:
    def __init__(self, id, osm):
        self.osm = osm
        self.id = id
        self.nds = []
        self.tags = {}

    def split(self, dividers):
        # slice the node-array using this nifty recursive function
        def slice_array(ar, dividers):
            for i in range(1,len(ar)-1):
                if dividers[ar[i]]>1:
                    #print "slice at %s"%ar[i]
                    left = ar[:i+1]
                    right = ar[i:]
                    
                    rightsliced = slice_array(right, dividers)
                    
                    return [left]+rightsliced
            return [ar]
            
        slices = slice_array(self.nds, dividers)
        
        # create a way object for each node-array slice
        ret = []
        i=0
        for slice in slices:
            littleway = copy.copy( self )
            littleway.id += "-%d"%i
            littleway.nds = slice
            ret.append( littleway )
            i += 1
            
        return ret
        
class OSM:
    def __init__(self, filename_or_stream):
        """ File can be either a filename or stream/file object."""
        nodes = {}
        ways = {}
        
        superself = self
        
        class OSMHandler(xml.sax.ContentHandler):
            @classmethod
            def setDocumentLocator(self,loc):
                pass
            
            @classmethod
            def startDocument(self):
                pass
                
            @classmethod
            def endDocument(self):
                pass
                
            @classmethod
            def startElement(self, name, attrs):
                if name=='node':
                    self.currElem = Node(attrs['id'], float(attrs['lon']), float(attrs['lat']))
                elif name=='way':
                    self.currElem = Way(attrs['id'], superself)
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nds.append( attrs['ref'] )
                
            @classmethod
            def endElement(self,name):
                if name=='node':
                    nodes[self.currElem.id] = self.currElem
                elif name=='way':
                    ways[self.currElem.id] = self.currElem
                
            @classmethod
            def characters(self, chars):
                pass

        xml.sax.parse(filename_or_stream, OSMHandler)
        
        self.nodes = nodes
        self.ways = ways
            
        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        for way in self.ways.values():
            if len(way.nds) < 2:       #if a way has only one node, delete it out of the osm collection
                del self.ways[way.id]
            else:
                for node in way.nds:
                    node_histogram[node] += 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.iteritems():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways

    #calcs the waylength in km
    def calclength(self,way):
        lastnode = None
        length = 0
        for node in way.nds:
            if lastnode is None:
                lastnode = self.nodes[node]
                continue

            # copyed from
            # http://stackoverflow.com/questions/5260423/torad-javascript-function-throwing-error
            R = 6371 # km
            dLat = (lastnode.lat - self.nodes[node].lat) * math.pi / 180
            dLon = (lastnode.lon - self.nodes[node].lon) * math.pi / 180
            lat1 = self.nodes[node].lat * math.pi / 180
            lat2 = lastnode.lat * math.pi / 180
            a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            d = R * c

            length += d

            lastnode = self.nodes[node]

        return length

    #return method for usage in matlab
    def convert2mat(self):
      vertexes = {}
      edges = []
      eid = 0
      for way in self.ways.itervalues():
          """ create 2 edges for each direction one """
          # add edge with way direction
          eid += 1
          edges.append(Edge(eid, way.id, way.nds, way.tags, self.calclength(way)))
          #print "eID: " + str(eid) + "\tdest: " + str(way.nds[-1]) + "\torg: " + str(way.nds[0])
          # Pseudocode auf gelben zettel einfuegen
          if way.nds[0] in vertexes:
              vertexes[way.nds[0]].add_edge(eid)
          else:
              node = self.nodes[way.nds[0]]
              vertexes[node.id] = Vertex(node.id, node.lon, node.lon, [], node.tags)
              vertexes[node.id].add_edge(eid)

          # add edge against way direction
          eid += 1
          reversed_nodes = way.nds[::-1]
          edges.append(Edge(eid, way.id, reversed_nodes, way.tags, self.calclength(way)))
          # Pseudocode auf gelben zettel einfuegen
          if reversed_nodes[0] in vertexes:
              vertexes[reversed_nodes[0]].add_edge(eid)
          else:
              node = self.nodes[reversed_nodes[0]]
              vertexes[node.id] = Vertex(node.id, node.lon, node.lon, [], node.tags)
              vertexes[node.id].add_edge(eid)

      # reduce node numbers

      # print edges matrix

      i = 0
      for ed in edges:
          i += 1
          print str(i) + ": " + ed.toString()
      # print edges matrix
      for v in vertexes.itervalues():
          print v.toString()


def main(argv=None):
    print "hallo\n"
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "h", ["help"])
        except getopt.error, msg:
             raise Usage(msg)
        # more code, unchanged
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
    #call the convert function
    G=read_osm(download_osm(-122.32,47.60,-122.31,47.61))
    #G=read_osm(download_osm(45.1919,5.7632,45.1951,5.7679))
    #plot([G.node[n]['data'].lat for n in G], [G.node[n]['data'].lon for n in G], ',')
    networkx.draw(G)
    #networkx.draw_random(G)
    plt.show()
    #plt.savefig("path.png")
    #print [G.node[n]['data'].lat for n in G]



if __name__ == '__main__':
    #print >>sys.stdout, "hallo2"
    print "Starting Programm"
    main()
