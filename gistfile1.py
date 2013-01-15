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
import urllib

def download_osm(left,bottom,right,top):
    """ Return a filehandle to the downloaded data."""
    from urllib import urlopen
    bbox = "%f,%f,%f,%f"%(left,bottom,right,top)
    #url = "http://api.openstreetmap.org/api/0.6/map?bbox=" + bbox
    
    url = "http://overpass-api.de/api/interpreter?data=" + urllib.quote("(way("+ bbox + ")[highway];>;);out;")
    print url
    
    #url = "data.osm"
    #url = "graph_in_OSM.osm"
    url = "tram_B.osm"
    #url = "grenoble_highway.osm"
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

        hw={'footway':1, 'cycleway':2, 'path':1, 'residental':4,'motorway':3,'trunk':3,'motorway_link':3,'primary':3,
                'secondary':3, 'tertiary':4, 'living_street':4, 'unclassified':4, 'service':4, 'track':2, 'steps':1,
                'bus':5, 'tram':6}
        if "highway" in tags and tags["highway"] in hw:
            self.highway = hw[tags["highway"]]
        else:
            self.highway = 1# if unknown its a footway

        self.access_foot = 1
        if "foot" in tags and tags["foot"] == "no":
            self.access_foot = 0
        self.access_bike = 1
        if "bicycle" in tags and tags["bicycle"] == "no":
            self.access_bike = 0

    def toString(self):
        return "" + str(self.dest) + ", '" + self.name.replace("'", "''") + "', " + str(self.length) + ", " + str(self.highway) + ", " + str(self.access_foot) + ", " + str(self.access_bike) + ";"

class Vertex:
    def __init__(self, id, lon, lat, eds, tags):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.eds = []
        if "name" in tags:
            self.name = tags["name"]
        else:
            self.name = "no name"
        self.tags = {}

    def add_edge(self, edge):
        self.eds.append(edge)

    def toString(self):
        tempe = [str(i) for i in self.eds] + ["0"]*(10 - len(self.eds))
        edges = ", ".join(tempe)
        return "'"+self.name.replace("'", "''") + "', " + edges + ", " + str(self.lon) + ", " + str(self.lat) + ", " + str(self.id) +  ";"


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

class Route:
    # only for relations with type=route
    def __init__(self, id, osm):
        self.osm = osm
        self.id = id
        self.stops = []
        self.platforms = []
        self.ways = []
        self.tags = {}
        
class OSM:
    def __init__(self, filename_or_stream):
        """ File can be either a filename or stream/file object."""
        nodes = {} # node objects
        ways = {}# way objects
        vways ={}# old ID: [list of new way IDs] to use relations
        routes = {} # to store the route relations
        
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
                elif name=='relation':
                    # important to ensure that nur relations of the type route are in the input file
                    # TODO fix it later to work generly
                    self.currElem = Route(attrs['id'], superself)
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nds.append( attrs['ref'] )
                elif name=='member':
                    if attrs['role'].split(':')[0]=='stop':
                        self.currElem.stops.append( attrs['ref'] )
                    elif attrs['role'].split(':')[0]=='platform':
                        self.currElem.platforms.append( attrs['ref'] )
                    elif attrs['role'].split(':')[0] in ['forward', 'backward', '']:
                        self.currElem.ways.append( attrs['ref'] )
                    #else:
                        #ignore it
                
            @classmethod
            def endElement(self,name):
                if name=='node':
                    nodes[self.currElem.id] = self.currElem
                elif name=='way':
                    ways[self.currElem.id] = self.currElem
                elif name=='relation':
                    routes[self.currElem.id] = self.currElem
                
            @classmethod
            def characters(self, chars):
                pass

        xml.sax.parse(filename_or_stream, OSMHandler)
        
        self.nodes = nodes
        self.ways = ways
        self.routes = routes
            
        """ prepare ways for routing """
        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        for way in self.ways.values():
            if len(way.nds) < 2:       #if a way has only one node, delete it out of the osm collection
                del self.ways[way.id]
            else:
                for node in way.nds:
                    #count public_transport=stop_position extra (to ensure a way split there)
                    if 'public_transport' in nodes[node].tags and nodes[node].tags['public_transport']=='stop_position':
                        node_histogram[node] += 2
                    else:
                        node_histogram[node] += 1

        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.iteritems():
            split_ways = way.split(node_histogram)
            vways[way.id]=[]#lockup to convert old to new ids
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
                vways[way.id].append(split_way.id)
        self.ways = new_ways
        self.vways = vways
        #for i in self.ways.itervalues():
          #print i.id

        """ prepare routes for routing """
        # TODO a lot
        new_ways = {}
        i = 0
        way_no = 0
        for r in self.routes.itervalues():
            route_type = r.tags['route']
            tw = None
            # to turn the ways in the right direction
            last_node = None
            for old_wayid in r.ways:
                # TODO handle old ways as a way?
                #bring the nodes in the right order
                nds = [self.ways[wayid] for wayid in self.vways[old_wayid]]

                if not last_node==None:
                    if last_node==nds[0]:
                        nds = nds
                    elif last_node==nds[-1]:
                        nds = nds[::-1]
                    else:#ERROR
                        print "ERROR: Route ["+str(r.id)+"] in Way ["+str(wayid)+"] is not connected to the previous"
                else:
                    nds = nds
                last_node = nds[-1]

                #skip if last stop was already reached
                if i>len(r.stops):
                    continue

                if r.stops[i] in nds:

                    # create a new way from now on
                    if not tw==None:
                        tw.nds.append(nds[:nds.index(r.stops[i])])#add all nodes up to the new stop_position
                        new_ways[tw.id] = tw

                        way_no += 1

                    tw = Way('special'+str(way_no)) #TODO
                    tw.tags = r.tags.append({'highway': route_type})
                    tw.nds = nds[nds.index(r.stops[i]):]#all nodes beginning with the stop

                    i += 1#jump to next stop_position
                elif not tw==None:
                    # add all nodes to tw if tw!=None
                    tw.nds.append(nds)
                else: #befor first station - nothing to add
                    continue

        self.ways.append(new_ways)


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
      vertexes = []
      edges = []
      node_lu = {}
      eid = 0
      nid = 1
      for way in self.ways.itervalues():
          if 'highway' not in way.tags:
              continue
          """ create 2 edges for each direction one """
          # add edge with way direction
          eid += 1
          edges.append(Edge(eid, way.id, way.nds, way.tags, self.calclength(way)))
          #print "eID: " + str(eid) + "\tdest: " + str(way.nds[-1]) + "\torg: " + str(way.nds[0])
          # Pseudocode auf gelben zettel einfuegen
          if way.nds[0] in node_lu:
              #print "org: "+ str(way.nds[0]) + "new: " + str(node_lu[way.nds[0]])
              vertexes[node_lu[way.nds[0]]-1].add_edge(eid)
          else:
              node = self.nodes[way.nds[0]]
              #print "add new id: " + str(node.id) + "=>" + str(nid)
              node_lu[str(node.id)] = nid # substitude the node id with array index
              vertexes.append(Vertex(node.id, node.lon, node.lon, [], node.tags))
              vertexes[nid-1].add_edge(eid)
              nid += 1

          # add edge against way direction
          eid += 1
          reversed_nodes = way.nds[::-1]
          edges.append(Edge(eid, way.id, reversed_nodes, way.tags, self.calclength(way)))
          # Pseudocode auf gelben zettel einfuegen
          if reversed_nodes[0] in node_lu:
              #print "org: "+ str(way.nds[0]) + "new: " + str(node_lu[way.nds[0]])
              vertexes[node_lu[reversed_nodes[0]]-1].add_edge(eid)
          else:
              node = self.nodes[reversed_nodes[0]]
              #print "add new id: " + str(node.id) + "=>" + str(nid)
              node_lu[node.id] = nid # substitude the node id with array index
              vertexes.append(Vertex(node.id, node.lon, node.lon, [], node.tags))
              vertexes[nid-1].add_edge(eid)
              nid += 1

      # reduce node numbers
      for e in edges:
          e.dest = node_lu[e.dest]

      # print edges matrix
      f = open('graph.m', 'w')

      i = 0
      f.write("\n%[destination node ID, name, length, highway (1:footway, 2:cycleway, 3:big_street, 4:small_street, 5:bus, 6:tram), footaccess (0/1), bikeaccess (0/1)]\n")
      f.write("edges = {\n")
      for ed in edges:
          i += 1
          #print str(i) + ": " + ed.toString()
          f.write( ed.toString()+"\n")
      f.write( "}\n\n")

      # print edges matrix
      i = 0
      f.write( "%[name, 10 fields with edges, lon, lat, original ID]\n")
      f.write( "nodes = {\n")
      for v in vertexes:
        i+=1
        #print str(i)+": "+ v.toString()
        f.write( v.toString() +"\n")
      f.write( "}\n")
      f.close()


def main(argv=None):
    print "hallosn"
    print sys.argv[0]
    print "hallosn"
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
    #G=read_osm(download_osm(-122.32,47.60,-122.31,47.61))
    G=read_osm(download_osm(45.1356,5.6623,45.2198,5.7889)) # ganz Grenoble
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
