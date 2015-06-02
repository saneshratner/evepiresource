#!/usr/bin/perl -w




#  Variables are:
#  1) SecStat
#    a) SecClass
#  2) Planet Type


#Table: 
# (secstat, secclass, planet_type, resource, mean, median, stddev, variance, min, max)


use IO::Handle;
use DBI;
#use strict;
use warnings;

use Abundance::Config qw ( debug_level );
use Abundance::Database qw ( connect planet_info_name planet_info_id get_planets_in_system );
use Abundance::EVEData;




my $debug  = $Abundance::Config::debug_level;

my $dbh;


my $stats_html = "/home/sratner/euni.puppytech.net/abundance_stats.html";


my $google_analytics = <<EOM;
<!-- Google Analytics Code -->
<script type="text/javascript">

  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', 'UA-21353540-1']);
  _gaq.push(['_setDomainName', '.puppytech.net']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();

</script>

<!-- End Google Analytics Code -->
EOM


#  Connect to database
$dbh = Abundance::Database::connect ();


#  First we are going to update the latest flag

$latelist_sql = "SELECT ID, planetID, submit_date, latest FROM planetAbundance ORDER BY planetID, submit_date, id";

$latelist_sth = $dbh->prepare ($latelist_sql);

$lateupd_sql = "UPDATE planetAbundance SET latest = ? WHERE ID = ?";
$lateupd_sth = $dbh->prepare ($lateupd_sql);

$earlyupd_sql = "UPDATE planetAbundance SET latest = ? WHERE planetID = ? AND ID <> ?";
$earlyupd_sth = $dbh->prepare ($earlyupd_sql);


$latelist_sth->execute () or die "Failure exec latelist_sth: " . $dbh->errstr;

$last_planet = 0;
#$last_id = 0;

@prev_row = ();

ROW:
while ( @rowarr = $latelist_sth->fetchrow_array() ) {
    my ($id, $pid, $date, $late)  = @rowarr;

    printf (STDERR "Testing $id (planet $pid) (late:$late) (sub:$date)\n") if $debug > 3;


    if ( $late eq 'Y' ) {
	$latecnt{$pid}++;
    }

    #  if we a second entry 
    if ( $pid != $last_planet ) {
	if ($last_planet !=  0 ) {
	    my ($id, $pid, $date, $late)  = @prev_row;
	    if ( ( $late ne 'Y' ) or ( ( defined $latecnt{$pid} ) and (  $latecnt {$pid} > 1))) {
		#  So we have not already set this one as the latest
		printf (STDERR "Adjusting pid $pid, for $id to be latest\n") if $debug > 3;
		$earlyupd_sth->execute ('N', $pid, $id);
		$lateupd_sth->execute ('Y', $id);
		$earlyupd_sth->finish();
		$lateupd_sth->finish();
	    }
	}
    }
	
    
    @prev_row = @rowarr;
    $last_planet = $pid;
}

$latelist_sth->finish();


# Fix up the security classes
$sql = "UPDATE planetAbundance SET securityClass = 'H' WHERE securityStatus >= 0.5";
$dbh->do ($sql) or die "Failure exec fix secClass: " . $dbh->errstr;
$sql = "UPDATE planetAbundance SET securityClass = 'L' WHERE securityStatus < 0.5 AND securityStatus > 0.0";
$dbh->do ($sql) or die "Failure exec fix secClass: " . $dbh->errstr;
$sql = "UPDATE planetAbundance SET securityClass = '0' WHERE securityStatus <= 0.0";
$dbh->do ($sql) or die "Failure exec fix secClass: " . $dbh->errstr;
$sql = "UPDATE planetAbundance SET securityClass = 'W' WHERE securityStatus LIKE 'W%'";
$dbh->do ($sql) or die "Failure exec fix secClass: " . $dbh->errstr;


# Now that we know the latest submission, 

#foreach $resource ( keys %resource_col_names ) {
#}

$sql =  "SELECT * FROM planetAbundance WHERE planetType = ?  AND securityClass = ? AND latest = 'Y'" ;
$type_class_sth = $dbh->prepare ($sql);

@fields_agr = ();
@fields_ind = ();

push (@fields_agr, sprintf ("count(planetID) AS cnt", $i));

$i = 0;
while ( $i < 5 ) {
    push (@fields_ind, sprintf ("resource%d", $i));
    push (@fields_agr, sprintf ("min(resource%d) AS min%d", $i, $i));
    push (@fields_agr, sprintf ("max(resource%d) AS max%d", $i, $i));
    push (@fields_agr, sprintf ("avg(resource%d) AS mean%d", $i, $i));
    push (@fields_agr, sprintf ("stddev(resource%d) AS stddev%d", $i, $i));
    push (@fields_agr, sprintf ("variance(resource%d) AS var%d", $i, $i));
    $i++;
}


$sql = sprintf ("SELECT planetType, securityClass, %s FROM planetAbundance WHERE latest = 'Y' GROUP BY planetType, securityClass", join (", ", @fields_agr));
$type_class_agr_sth = $dbh->prepare ($sql);


$sql = "INSERT INTO resourceStats (planetType, securityClass, resource, min, max, mean, stddev, variance, cnt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
$ins_pla_res_sth=  $dbh->prepare ($sql);
$sql = "UPDATE resourceStats SET min=?, max=?, mean=?, stddev=?, variance=?, cnt=? WHERE planetType=? AND securityClass=? AND resource=?";
$upd_pla_res_sth=  $dbh->prepare ($sql);
$sql = "SELECT * FROM resourceStats WHERE planetType=? AND securityClass=? AND resource=?";
$probe_pla_res_sth = $dbh->prepare ($sql);


$type_class_agr_sth->execute ();

while ( $row_hashr = $type_class_agr_sth->fetchrow_hashref () ) {
    $class = defined ($row_hashr->{securityClass}) ? $row_hashr->{securityClass} : "undef";
    $ptypename = $planet_types {$row_hashr->{planetType}};
    @reslist = @{ $resources {$ptypename}->{res_map}};
    printf (STDERR "ROW: Type (%d) (%s) / Class (%s) / Count(%d) \n", $row_hashr->{planetType}, $ptypename, $class, $row_hashr->{cnt}) if $debug > 1;
    $i = 0;
    while ($i < 5) {
	$resname = $reslist[$i];
	printf (STDERR "    R%d (%s): Min(%d), Max(%d), Mean(%f), StdDev(%f), Var(%f)\n", $i, $resname,
		$row_hashr->{"min$i"},
		$row_hashr->{"max$i"},
		$row_hashr->{"mean$i"},
		$row_hashr->{"stddev$i"},
		$row_hashr->{"var$i"}) if $debug > 1;

	$probe_pla_res_sth->execute ($row_hashr->{planetType}, $class, $resname);
	if ( defined $probe_pla_res_sth->fetchrow_arrayref() ) {
	    my $rv;
	    
	    $rv = $upd_pla_res_sth->execute (
		$row_hashr->{"min$i"},
		$row_hashr->{"max$i"},
		$row_hashr->{"mean$i"},
		$row_hashr->{"stddev$i"},
		$row_hashr->{"var$i"}, 
		$row_hashr->{cnt},
		$row_hashr->{planetType}, $class, $resname) or do {
		    printf (STDERR "Failure update %s, %s, %s: %s\n", $row_hashr->{planetType},
			    $class, $resname, $upd_pla_res_sth->errstr) if $debug > 0;
	    };
	    $upd_pla_res_sth->finish ();

	    printf (STDERR "Update, result = %s\n", $rv) if $debug > 2;
	}
	else {
	    $ins_pla_res_sth->execute ($row_hashr->{planetType}, $class, $resname, 
				       $row_hashr->{"min$i"},
				       $row_hashr->{"max$i"},
				       $row_hashr->{"mean$i"},
				       $row_hashr->{"stddev$i"},
				       $row_hashr->{"var$i"}, 
				       $row_hashr->{cnt});	
	    $ins_pla_res_sth->finish ();
	    printf (STDERR "Insert\n") if $debug > 2;
	}
	$probe_pla_res_sth->finish ();

	
	$i++;
    }
    
    
}

$type_class_agr_sth->finish ();


#  Now scan through the individual lines to generate medians and such.
foreach $ptype ( keys %planet_types ) {
    foreach $secclass ( 'H', 'L', '0', 'W') {
	$type_class_sth->execute ($ptype, $secclass) or die "Failure exec type_class_sth: " . $dbh->errstr;

	while ( $row_hashr = $type_class_sth->fetchrow_hashref () ) {
	    


	}
	
	$type_class_sth->finish ();
    }
}

%secclassnames = ( "H" => "High", "L" => "Low", "0" => "0.0", "W" => "WH" );

$sql = "SELECT * FROM resourceStats WHERE planetType = ? AND securityClass = ? AND resource = ?";
$stats_sth= $dbh->prepare ($sql);

%all_resources = ();
%best_mean = ();

printf ("<html>\n<head><title>Eve University Abundance Project Statistics</title> $google_analytics  </head>\n<body>\n<h1>Eve University Abundance Project Statistics</h1>\n");

printf ('You can contribute to the data set by <a href="abundance_estimate.cgi">submitting your screenshots here</a>.<p>' . "\n");

printf ("The format of this table has the planet type in the columns, and the resources in the rows.  Therefore the amount of Aqueous Liquids from the Barren planets in the data set can be found in the upper left corner, etc.  Each cell has the abundance broken down by security status of the systems.  Each security status entry is in the form <br/><br/> Minimum - Average - Maximum (sample count) <p>\nCells in red indicate that this is the best type of planet to extract that resource.<p>\n");


printf ('<table border="1" style="font-size:x-small"><tr><th>Resource</th>' . "\n");

PTYPE:
foreach $ptype ( sort  keys %resources ) {
    $ptypeid = $resources{$ptype}->{typeid};
    @res_list = @{$resources{$ptype}->{res_map}};

    if ( ( $ptype eq "Unknown") or ( $ptype eq "Shattered" ) ) {
	next PTYPE;
    }

    foreach $res (@res_list) {
	$cell{"$ptype/$res"} = "";
	if ( defined $all_resources {$res} ) {
	    $all_resources {$res} = $all_resources {$res}  . "," . $ptype;
	}
	else {
	    $all_resources {$res} =  $ptype;
	}


	@lines = ();
	foreach $secclass ( 'H', 'L', '0', 'W') {
	    printf (STDERR "Querying $sql ($ptypeid, $secclass, $res)\n") if $debug > 3;
	    $stats_sth->execute ($ptypeid, $secclass, $res);
	    
	    if ( defined ($rowhr = $stats_sth->fetchrow_hashref () ) ) {
		#$line = sprintf ("%4s: %d-%d, avg %5.2f +/- %5.2f (%d samples)", 
		#		 $secclassnames{$secclass}, 
		#		 $rowhr->{min}, $rowhr->{max},
		#		 $rowhr->{mean}, $rowhr->{stddev}, 
		#		 $rowhr->{cnt});
		$line = sprintf ("%4s: %d-%5.2f-%d (%d)", 
				 $secclassnames{$secclass}, 
				 $rowhr->{min}, 
				 $rowhr->{mean},
				 $rowhr->{max},
				 $rowhr->{cnt});
		

		if ( $secclass eq "H" ) {
		    	if ( defined $best_mean {$res} ) {
			    ($cur_val, $cur_ptype) = split (",", $best_mean{$res});
	    
			    if ( $rowhr->{mean} > $cur_val ) {
				$best_mean{$res} = sprintf ("%f,%s", $rowhr->{mean}, $ptype);
			    }
			}
			else {
			    $best_mean{$res} = sprintf ("%f,%s", $rowhr->{mean}, $ptype);
			}
		}

	    }
	    else {
		$line = sprintf ("%4s: No Data", $secclassnames{$secclass});
	    }

	    $stats_sth->finish ();

	    push (@lines, $line);
	}
	
	$cell{"$ptype/$res"} = join ("<br />", @lines);
    }

    printf ("<th>$ptype</th>");
}

printf ("</tr>\n");


foreach $res ( sort keys %all_resources ) {
    $best_ptype = "";

    printf ("<tr><td>$res</td>");

    if ( defined ( $best_mean{$res} ) ) {
	($cur_val, $best_ptype) = split (",", $best_mean{$res});
    }

    printf (STDERR "Best Mean = %s\n", $best_mean{$res}) if $debug > 2;


  PTYPE:
    foreach $ptype ( sort keys %resources ) {
	if ( ( $ptype eq "Unknown") or ( $ptype eq "Shattered" ) ) {
	    next PTYPE;
	}

	printf ("<td>");
	if ( defined $cell{"$ptype/$res"} ) {
	    if ( $ptype eq $best_ptype ) {
		$colour = 'style="color:red"';
	    }
	    else {
		$colour = "";
	    }

	    printf ("<p %s>%s</p>", $colour, $cell{"$ptype/$res"});
	}
	printf ("</td>");
    }

    printf ("</tr>\n");
}

printf ("</table>\n");

printf ("</body>\n</html>\n");
