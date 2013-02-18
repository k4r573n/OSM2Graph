# OSM to Graph

This Program provides a routeable graph generated out of 
OpenstreetMap-data. Therefore are highways as well as 
public transportation lines taken into account.

## parsed tagging
- [Highway](http://wiki.openstreetmap.org/wiki/Highway)
- [Proposed_features/Public_Transport](http://wiki.openstreetmap.org/wiki/Proposed_features/Public_Transport)
- [Proposed_features/Route_Segments](http://wiki.openstreetmap.org/wiki/Proposed_features/Route_Segments)

## Problems
-   Till now there is no edge to continue routing from a tram platform
-   not now possible to switch between platforms of the same station

## Future Work
-   implement as well the Weighted Indoor Routing Graph (WIRG)
    according to:
    Goetz, M.; Zipf, A. Formal definition of a user-adaptive and length-optimal
    routing graph for
    complex indoor environments. Geo-Spat. Inf. Sci. 2011, 14, 119-128.
-   provide a export function to a neo4j database

## Thanks to
- brianw and his [osmgeocode](http://github.com/brianw/osmgeocode) which is the base of
- Abraham Flaxman and his [gistfile1.py](https://gist.github.com/aflaxman/287370/) which is the base of this program
- Teddych who has introduced the [public_transport Proposal](http://wiki.openstreetmap.org/wiki/Proposed_features/Public_Transport) 

## Links
[OpenstreetMap Wiki Page](http://wiki.openstreetmap.org/wiki/Braunschweig/Transportation/Routing) (in German)
