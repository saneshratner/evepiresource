#!/usr/bin/perl -w


use strict;

package Abundance::Database;

use base 'Exporter';
our @EXPORT_OK = qw ( connect 
       planet_info_name planet_info_id 
       eve_id_to_name find_current_abundance 
       get_planets_in_system );


use Abundance::Config;
use Abundance::EVEData;


my ($dsn, $dbuser, $dbpass) = 
    ($Abundance::Config::dsn
     , $Abundance::Config::dbuser
     , $Abundance::Config::dbpass  );

my $dbh;





my $find_planet_sql = "SELECT itemID, m.typeID, solarSystemID, constellationID, regionID, celestialIndex, itemName, security, wormholeClassID, celestialIndex, typeName, graphicID from mapDenormalize m JOIN invTypes t ON m.typeID = t.typeID LEFT JOIN mapLocationWormholeClasses c ON m.regionID = c.locationID";
    

our %resource_col_names = (
    "Aqueous Liquids" => "aqueous_liquids",
    'Autotrophs' => 'autotrophs',
    'Base Metals' => "base_metals", 
    'Carbon Compounds' => 'carbon_compounds', 
    'Complex Organisms' => 'complex_organisms',
    'Felsic Magma' => 'felsic_magma',
    'Heavy Metals' => 'heavy_metals',
    'Ionic Solutions' => 'ionic_solutions',
    'Micro Organisms' => 'micro_organisms', 
    'Noble Metals' => 'noble_metals',
    'Noble Gas' => 'noble_gas', 
    'Non-CS Crystals', 'noncs_crystals',
    'Planktic Colonies' => 'planktonic_colonies',
    'Reactive Gas' => 'reactive_gas',
    'Suspended Plasma' => 'suspended_plasma' );




#  Connect to database

sub connect {
    if ( $dbh = DBI->connect($dsn,$dbuser,$dbpass) ) {
	prep ($dbh);
    }
    else {
	die ("Abundance::Database::connect: Failed to connect to database $dsn\n");
    }

    return $dbh;
}

my $find_planetname_sth;
my $find_planetid_sth;
my $search_planet_sth;
my $system_planets_sth;
my $wh_class_sth;
my $const_planets_sth;
my $region_consts_sth;
my $regionlist_sth;
my $stats_sth;

my %resources = %Abundance::EVEData::resources;

my %planet_types = %Abundance::EVEData::planet_types;




sub prep ($) {
    my $dbh = shift;

    $find_planetname_sth = $dbh->prepare ("$find_planet_sql WHERE itemName = ?");  #  eg "Aldrat V"
    $find_planetid_sth = $dbh->prepare ("$find_planet_sql WHERE itemID = ?");  #  eg "31002411"
    #my $save_abundance_sth = $dbh->prepare ("INSERT INTO  FROM ... ");

    $search_planet_sth = $dbh->prepare ("SELECT itemID, m.typeID, solarSystemID, constellationID, regionID, celestialIndex, itemName, security, wormholeClassID, celestialIndex, planetID from mapDenormalize m LEFT JOIN mapLocationWormholeClasses c ON m.regionID = c.locationID LEFT JOIN planetAbundance a ON m.itemID = a.planetID WHERE groupID  = 7 AND itemName LIKE CONCAT ('%', ?, '%') ORDER BY submit_date DESC")  or die "Failure prepare search_planet_sth: " . $dbh->errstr;  #  eg "Aldrat V"

    $system_planets_sth = $dbh->prepare ("SELECT itemID, m.typeID, solarSystemID, constellationID, regionID, celestialIndex, itemName, security, wormholeClassID, celestialIndex, planetID from mapDenormalize m LEFT JOIN mapLocationWormholeClasses c ON m.regionID = c.locationID LEFT JOIN planetAbundance a ON m.itemID = a.planetID WHERE groupID  = 7 AND solarSystemID = ? GROUP BY itemID")  or die "Failure prepare search_planet_sth: " . $dbh->errstr;  #  eg ""

    $wh_class_sth = $dbh->prepare ("SELECT itemID, itemName, typeID, groupID, solarSystemID, regionID, wormholeClassID FROM mapDenormalize m LEFT JOIN mapLocationWormholeClasses c ON m.regionID = c.locationID  WHERE itemID = ?");

    $const_planets_sth = $dbh->prepare ("SELECT solarSystemID, n.itemName as solarSystemName, count(m.itemID) as planetCount, count(planetID) as enteredCount FROM mapDenormalize m JOIN eveNames n ON n.itemID = m.solarSystemID LEFT JOIN planetAbundance a ON m.itemID = a.planetID  WHERE m.groupID = 7 AND constellationID = ? GROUP BY solarSystemID") or die "Failure prepare const_planets_sth: " . $dbh->errstr;  #  eg "200000498"


    $region_consts_sth = $dbh->prepare ("SELECT constellationID,n.itemName as constellationName, count(m.itemID) as planetCount, count(planetID) as enteredCount FROM mapDenormalize m JOIN eveNames n ON n.itemID = m.constellationID LEFT JOIN planetAbundance a ON m.itemID = a.planetID  WHERE m.groupID = 7 AND regionID = ? GROUP BY constellationID  ");

    $regionlist_sth = $dbh->prepare ("SELECT * FROM mapRegions ORDER BY regionName");

    $stats_sth = $dbh->prepare ("SELECT * FROM resourceStats WHERE planetType = ? AND securityClass = ? AND resource = ?");

    #  if (all the xxx_sth prepare-s worked) then
    return 0;

}


	    #  At this point we can look up the planet in the database.
	    #   SELECT * FROM eveNames WHERE typeID = 5 AND itemName = ?
	    #     $systemid = $res->{itemID}
	    #   SELECT * FROM mapDenormalize WHERE systemID = ? AND celestialIndex = ? ", $systemid, $planet_number
	    #     $planet_typeid = $res->{typeID}; $planet_type = $res_types {$planet_typeid};
	    #     $planet_id = $res->{itemID};
	    #   SELECT itemID,d.typeID, solarSystemID, constellationID, regionID, celestialIndex, itemName, security, celestialIndex, typeName, graphicID from mapDenormalize d JOIN invTypes t ON d.typeID = t.typeID where itemName = ?;  eg "Aldrat V"
	    #
	    #   For looking up the amount of progress in this constellation
	    # SELECT solarSystemID, n.itemName as solarSystemName, count(m.itemID) as planetCount, count(planetID) as enteredCount FROM mapDenormalize m JOIN eveNames n ON n.itemID = m.solarSystemID LEFT JOIN planetAbundance a ON m.itemID = a.planetID  WHERE m.groupID = 7 AND constellationID = 20000498 GROUP BY solarSystemID;

	    




sub planet_info_id ($) {
    my $planet_id = shift;
    my $planet_info;
    
    $find_planetid_sth->execute($planet_id);
    $planet_info = $find_planetid_sth->fetchrow_hashref();

    return $planet_info;
}

sub planet_info_name ($) {
    my $planet_name = shift;
    my $planet_info;
    
    $find_planetname_sth->execute ($planet_name);
    $planet_info = $find_planetname_sth->fetchrow_hashref() ;

    return $planet_info;
}

sub query_planet_list_name ($) {
    my $planet_name = shift @_;

    my @planet_list;
    my $planet_info;

    $search_planet_sth->execute ($planet_name) or die "Failure exec search_planet_sth: " . $dbh->errstr;
    
    
    while ( $planet_info = $search_planet_sth->fetchrow_hashref() )  {
	push (@planet_list , $planet_info);
    }

    $search_planet_sth -> finish ();

    return (@planet_list);
}


sub query_planet_list_system ($) {
    my $systemid = shift @_;
    
    my @planet_list;
    my $planet_info;

    $system_planets_sth->execute ($systemid);
    while ( $planet_info = $system_planets_sth->fetchrow_hashref() )  {
	push (@planet_list , $planet_info);
    }
    
    $system_planets_sth -> finish ();

    return @planet_list;
}


sub query_planets_in_constellation ($) {
    my $const_id = shift @_;

    my @planet_hasharr = ();
    my $hashref;

    $const_planets_sth->execute ($const_id) or die "Failure exec const_planets_sth: " . $dbh->errstr;

    while ( $hashref = $const_planets_sth->fetchrow_hashref() )  {
	push (@planet_hasharr, { 'solarSystemID' => $hashref->{solarSystemID}
				 , 'solarSystemName' => $hashref->{solarSystemName}
				 , 'enteredCount' => $hashref->{enteredCount}
				 , 'planetCount' => $hashref->{planetCount}
	      });
    }

    $const_planets_sth -> finish ();	
    

    return @planet_hasharr;
}


sub query_constellations_in_region ($) {
    my $regionid = shift @_;

    my $hashref;
    my @const_hasharr = ();

    $region_consts_sth->execute ($regionid) or die "Failure exec region_consts_sth: " . $dbh->errstr;
    

    while ( $hashref = $region_consts_sth->fetchrow_hashref() )  {
	my $field;
	my $newhash = {};
	for $field ( 'constellationID', 'constellationName', 'enteredCount', 'planetCount' ) {
	    $newhash->{$field} = $hashref->{$field};
	}
	push (@const_hasharr, $newhash);
    }

    $region_consts_sth -> finish ();	

    return @const_hasharr;
}


sub list_regions {
    my $hashref;
    my %regions = ();

    $regionlist_sth->execute () or die "Failure exec regionlist_sth: " . $dbh->errstr;
    
    
    while ( $hashref = $regionlist_sth->fetchrow_hashref() )  {
	$regions {$hashref->{regionName}} = $hashref->{regionID};
    }

    $regionlist_sth -> finish ();	
    
    return %regions;
}



my $eveid_to_name_sth;  # this is static between calls
sub eve_id_to_name ($) {
    my $id = shift;
    my $infohash;
    my $name = "???";
    

    if ( ! defined $eveid_to_name_sth ) {
	$eveid_to_name_sth = $dbh->prepare ("SELECT * FROM eveNames WHERE itemID = ?");
    }

    $eveid_to_name_sth->execute ($id);

    if ( $infohash = $eveid_to_name_sth->fetchrow_hashref() ) {
	$name = $infohash->{itemName};
    }
   
    $eveid_to_name_sth->finish();

    return $name;
}

my $current_abundance_sth;  # this is static between calls
sub find_current_abundance ($) {
    my $planet_id = shift;
    my @resource_vals_fields ;
    my $infohash;

    if ( ! defined $current_abundance_sth ) {
	$current_abundance_sth = $dbh -> prepare ("SELECT * FROM planetAbundance WHERE planetID = ? ORDER BY submit_date DESC");
    }

    $current_abundance_sth-> execute ($planet_id);


    if ( defined ($infohash = $current_abundance_sth->fetchrow_hashref ()) ) {
	for ( my $i = 0; $i <= 4; $i++) {
	    $resource_vals_fields [$i] = $infohash->{"resource$i"};
	}
    }


    $current_abundance_sth->finish ();

    return @resource_vals_fields;
}


sub get_planets_in_system ($) {
    my $system_id = shift;
    my @planet_list = ();
    my $planet_info;

    $system_planets_sth->execute ($system_id);
    while ( $planet_info = $system_planets_sth->fetchrow_hashref() )  {
	push (@planet_list , $planet_info);
    }
    
    $system_planets_sth -> finish ();
    
    return (@planet_list);
}




sub stats_for ($$$) {
    my ($planet_type_id, $secclass, $resname) = @_;
    my $rowhr;

    $stats_sth->execute ($planet_type_id, $secclass, $resname);

    $rowhr = $stats_sth->fetchrow_hashref ();
    return $rowhr;
}



sub save_planet ($$$$$$$$) {
    my $planet_id = shift @_;
    my $remote_host = shift @_;
    my $resource_values = shift @_;
    my $planet_type = shift @_;
    my $planet_type_id = shift @_;
    my $planet_name = shift @_;
    my $secstat = shift @_;
    my $wh_class = shift @_;


    my @resource_values = @{$resource_values};
    
    my @resource_labels;
    
    my @resource_fields = ('resource0', 'resource1', 'resource2', 'resource3', 'resource4');
    my $planet_info;
    
    my $can_proceed  = 1;


    if ( defined $resources{$planet_type} ) {
	@resource_labels = @{$resources{$planet_type}->{res_map}};

	for ( my $i = 0; $i <= $#resource_labels; $i++) {
	    $resource_fields[$i] = $resource_col_names {$resource_labels[$i]};
	}
    }
    else {
	my $found = 0;
	#  Try looking up the planet again


	if ( $planet_info = planet_info_id ($planet_id) )  {
	    $planet_type = $planet_types {$planet_info->{typeID}};
	    
	    
	    if ( defined $resources{$planet_type} ) {
		@resource_labels = @{$resources{$planet_type}->{res_map}};
		
		for ( my $i = 0; $i <= $#resource_labels; $i++) {
		    $resource_fields[$i] = $resource_col_names {$resource_labels[$i]};
		}
		
		$found = 1;
	    }
	}
	
	if ( $found < 1 ) {
	    #@resource_labels = @{$resources{"Unknown"}->{res_map}};
	    printf ("Failure determining resources on type $planet_type <br />\n");
	    $can_proceed = 0;
	}
    }
    
    
    
    if ( ! defined $planet_type_id  ) {
	$planet_type_id = $resources{$planet_type}->{typeid};
    }


    #printf ("<pre> PlanName=$planet_name, Sys=$system, Num =$planet_number, Sec=$secstat, Type=$planet_type, vals=(%s) \n</pre>",   join (", ", @resource_vals_fields));
    
    #printf (" def = %d (%s)\n ", defined %res_map, join (", ", keys (%res_map)));


    # Build the insert query
    my $query_str = sprintf ("INSERT INTO planetAbundance (planetID, planetType, planetName, securityStatus, wh_class, submit_from, submit_date, resource0, resource1, resource2, resource3, resource4, %s, %s, %s, %s, %s) VALUES (%d, %d, '%s', '%s', '%s', '%s', now(), %d, %d, %d, %d, %d, %d, %d, %d, %d, %d )", @resource_fields, $planet_id, $planet_type_id, $planet_name, $secstat, $wh_class, $remote_host, @resource_values, @resource_values );

    printf ("<!-- SQL stmt = %s -->\n", $query_str);
    
    my $row_count = $dbh->do ($query_str);
    printf ("<!-- Rows Affected = %d  -->\n", $row_count);
    if ( $dbh->errstr () ) {
	printf ("Error = %s\n", $dbh->errstr());
    }

    
    return 0;
}

1;
