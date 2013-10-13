#!/usr/bin/perl 

use CGI qw(:standard);
use CGI::Carp qw/fatalsToBrowser/;
use DBI;
use Text::CSV;
use strict;
use warnings;





my %resources = ( 
     'Barren' => { res_map =>  [ 'Aqueous Liquids', 'Base Metals', 'Carbon Compounds', 'Micro Organisms', 'Noble Metals' ],
                 typeid => 2016 },
    'Gas' =>  { res_map => [ 'Aqueous Liquids', 'Base Metals', 'Ionic Solutions', 'Noble Gas', 'Reactive Gas' ],
		typeid => 13 },
    'Ice' => { res_map => [ 'Aqueous Liquids', 'Heavy Metals', 'Micro Organisms', 'Noble Gas', 'Planktic Colonies' ] ,
	       typeid => 12 },
    'Lava' => { res_map => [ 'Base Metals', 'Felsic Magma', 'Heavy Metals',  'Non-CS Crystals', 'Suspended Plasma' ] ,
	       typeid => 2015 },
    'Oceanic' => { res_map => [ 'Aqueous Liquids', 'Carbon Compounds', 'Complex Organisms', 'Micro Organisms', 'Planktic Colonies' ] ,
	       typeid => 2014 },
    'Plasma' => { res_map => [ 'Base Metals', 'Heavy Metals', 'Noble Metals', 'Non-CS Crystals', 'Suspended Plasma' ],
	       typeid => 2063 },
    'Storm' => { res_map => [ 'Aqueous Liquids', 'Base Metals', 'Ionic Solutions',  'Noble Gas', 'Suspended Plasma' ],
	       typeid => 2017 },
    'Temperate' => { res_map => [ 'Aqueous Liquids', 'Autotrophs', 'Carbon Compounds', 'Complex Organisms', 'Micro Organisms' ],
	       typeid => 11 },
    'Shattered' => { res_map => [ 'R1', 'R2', 'R3', 'R4', 'R5' ] ,
	       typeid => 30889 },
    'Unknown' => { res_map => [ 'Resource 1', 'Resource 2', 'Resource 3', 'Resource 4', 'Resource 5' ], typeid => 999999 }
		    
    );

my %planet_types;

foreach my $name ( keys %resources ) {
    my $typeid = $resources{$name}->{typeid};
    $planet_types {$typeid} = $name;
}

my %resource_col_names = (
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



my $dsn = "DBI:mysql:database=puppy_euni;host=mysql.puppytech.net";
my $dbuser = "eveuser";
my $dbpass = "password";
my $dbh;


1;



sub db_dump {
    my @column_names = ( 'planetID', 'planetType', 'planetName', 'securityStatus', 
			 'resource0', 'resource1', 'resource2', 'resource3', 'resource4', 'submit_date', 
			 'aqueous_liquids', 'autotrophs', 'base_metals', 
			 'complex_organisms', 'carbon_compounds', 
			 'felsic_magma', 'heavy_metals', 'ionic_solutions', 
			 'micro_organisms', 'noble_gas', 'noble_metals', 
			 'noncs_crystals', 'planktonic_colonies', 
			 'reactive_gas', 'suspended_plasma' );
    my $sql = sprintf ("SELECT %s
                           FROM planetAbundance 
                           ORDER BY planetID, submit_date DESC", 
		       join (", ", @column_names));
    my $dbdump_sth = $dbh->prepare ($sql);
    my %seen_planets = ();
    my $csv = Text::CSV->new ();
    my $planet_info;

    
    $dbdump_sth->execute() or die "Failure exec dbdump_sth: " . $dbh->errstr;
    
    $csv->combine (@column_names);
    print $csv->string . "\n";
    
    while ( $planet_info = $dbdump_sth->fetchrow_hashref() )  {
	my $pid = $planet_info->{planetID};
	if ( ! defined ( $seen_planets{$pid} )) {
	    my $i;
	    my @values = ();
	    my $field;
	    
	    $seen_planets{$pid} = $pid;
	    
	    $i = 0;
	    foreach $field (@column_names) {
		$values[$i] = $planet_info->{$field};
                if ( $field eq "planetType" ) {
                    $values[$i] = $planet_types {$values[$i]};
                }
		$i++;
	    }
	    
            $csv->combine (@values);
	    print $csv->string . "\n";
	}
	else {
	    #Skip
	}
    }
    
    $dbdump_sth->finish ();
}



my $query = new CGI;
print $query->header('text/csv');
#print $query->start_html ('PI Abundance Estimator');


#Connect to database
$dbh = DBI->connect($dsn,$dbuser,$dbpass);


db_dump();
