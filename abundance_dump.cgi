#!/usr/bin/perl 

use CGI qw(:standard);
use CGI::Carp qw/fatalsToBrowser/;
use DBI;
use Text::CSV;
use strict;
use warnings;

use Abundance::Config qw ( debug_level );
use Abundance::Database qw ( connect planet_info_name planet_info_id get_planets_in_system );
use Abundance::EVEData;



my $dbh;

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
                    $values[$i] = $Abundance::EVEData::planet_types {$values[$i]};
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
#$dbh = DBI->connect($dsn,$dbuser,$dbpass);
$dbh = Abundance::Database::connect();

db_dump();
