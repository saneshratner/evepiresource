#!/usr/bin/perl 

use CGI qw(:standard);
use CGI::Carp qw/fatalsToBrowser/;
use IO::Handle;
use DBI;
use POSIX;
use strict;
#use warnings;

use lib '.';

use Abundance::Config qw ( debug_level );
use Abundance::Image qw (extract_image extract_image_file);
use Abundance::Database qw ( connect planet_info_name planet_info_id get_planets_in_system );
use Abundance::EVEData;


$CGI::POST_MAX=1024 * 2000;  # max 100K posts


my $debug  = $Abundance::Config::debug_level;
my $write_orig = $Abundance::Config::write_orig;


my $img_base = 'http://wiki.eveuniversity.org/w/images';


my %resources = %Abundance::EVEData::resources;

my %planet_types = %Abundance::EVEData::planet_types;

my %resource_col_names = %Abundance::Database::resource_col_names;



#my $dbh;
my $imagedir = $Abundance::Config::imagedir;

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




my $query = new CGI;

print $query->header();
print $query->start_html (-title => 'PI Abundance Estimator',
    -head => $google_analytics);
print $query->h1 ("PI Abundance Estimator") . "\n";

my @names = $query -> param;

my $planet_type = $query->param ('planet_type');
my $planet_name = $query->param ('planet_name');
my $secstat  = $query->param ('secstat');

#  TypeID comes from invTypes (typeID, typeName)







sub show_planet_form ($$) {
    my $planet_id = shift;
    my $query = shift;

    my @resource_vals_fields;
    my @resource_values;
    
    my $recall_url = $query->url (-relative=>1);

    my $planet_info;
    my ($systemid, $systemname, $planet_number, $secstat, $wh_class, $show_secstat, $planet_type_id);

    my $resblockfile;
    my $image;
    my $planet_name_w_img;

    if ( $planet_info = planet_info_id ($planet_id) )  {
	$systemid = $planet_info->{solarSystemID};
	$systemname = eve_id_to_name ($systemid);
	$planet_number = $planet_info->{celestialIndex};
	$wh_class = $planet_info->{wormholeClassID};
	$secstat = $planet_info->{security}; #sprintf ("%.1f", $planet_info->{security});
	$show_secstat = (($wh_class <= 6) && ($wh_class >= 1) ) ? sprintf ("W%d", $wh_class) :  sprintf ("%.1f", $planet_info->{security});
	$planet_name = $planet_info->{itemName}; 
	
	
	$planet_type = $planet_types {$planet_info->{typeID}};
	$planet_type_id = $planet_info->{typeID};
	if ( ( defined $resources{$planet_type} ) && defined $resources{$planet_type}->{img}) {

	    $image = sprintf ("%s/%s", $img_base, $resources {$planet_type}->{img});
	    #$image = $query->img (src=>$image, align=> 'RIGHT', alt=>$planet_type);
	    $image = sprintf ('<img src="%s"  align="RIGHT" alt="%s"', $image, $planet_type);
	}
	else {
	    $image = "";
	}
	
	$query->param ('system', $systemid);
	$query->param ('planet_number', $planet_number);
	$query->param ('secstat', $show_secstat);
	$query->param ('planet_type', $planet_type);
    }
    else {
	printf ("Failed to find planetid %d\n", $planet_id);
    }


    @resource_vals_fields = find_current_abundance ($planet_id);

    my @resource_labels;
    
    if ( defined $resources{$planet_type} ) {
	@resource_labels = @{$resources{$planet_type}->{res_map}};
    }
    else {
	@resource_labels = @{$resources{"Unknown"}->{res_map}};
    }
    
    if ( $#resource_values < 4 ) {
	@resource_values = @resource_vals_fields;
    }
    
    for ( my $i = 0; $i <= $#resource_values; $i++ ) {
	$query->param(-name => "resource$i", -value =>$resource_values[$i]) ;
	
	#printf ("Setting %s to %s <br />\n", "resource$i", $query->param ("resource$i"));
	
    }
    


    print "<!-- wh_class = $wh_class -->\n";

    print $query->start_form (-action=>$query->url(-relative=>1));
    
    print $query->hidden (-name => 'planet_id', -default=> $planet_id), 
          $query->hidden(-name=> 'planet_type_id', -default=> $planet_type_id), 
          $query->hidden(-name => 'planet_name', -default=> $planet_name), 
          $query->hidden(-name => 'which_form', -default=> "show_planet") . "\n";

    $planet_name_w_img = $planet_name . " " . $image;
    
    print table({-border=>undef},
		Tr({-align=>'LEFT',-valign=>'TOP'},
		   [
		    td(['Planet Name', $planet_name . " " . $image, '']),
		    #td(['Planet Name', $planet_name, '']),
		    td(['System', "<a href=\"$recall_url?search=system&systemid=$systemid\">$systemname</a>", '']),
		    td(['Planet Number' , $planet_number, '']),
		    td(['Security Status' , $show_secstat, '0.0-1.0, W1-6 for wormholes']),
		    #td(['Planet Type' , $query->popup_menu(-name=>'planet_type',
		    #				       -values=>['Barren', 'Gas', 'Ice', 'Lava', 'Oceanic', 'Plasma', 
		    #						 'Storm', 'Temperate']), '']),
		    td(['Planet Type', $query->hidden(-name=>'planet_type', -default=>$planet_type) . " ".  $planet_type, '']),
		    td(['Snapshot File' , $query->filefield(-name=> 'snapfile'), 'Submit a screenshot']),
		    td([$resource_labels[0] , $query->textfield(-name=> 'resource0', -override=>0), 'or Fill in abundance values']),
		    td([$resource_labels[1] , $query->textfield(-name=> 'resource1'), '']),
		    td([$resource_labels[2] , $query->textfield(-name=> 'resource2'), '']),
		    td([$resource_labels[3] , $query->textfield(-name=> 'resource3'), '']),
		    td([$resource_labels[4] , $query->textfield(-name=> 'resource4'), '']),
                    "\n"
		   ]
		)
	);
    print "\n" . $query->submit(-name=>'Submit');
    
    print "\n" . $query->end_form();


    $resblockfile = sprintf ("%s/%s-%s-resblock.png", $imagedir, $systemid, $planet_number);

    if ( -r $resblockfile ) {
		printf ("<br /> <img src=\"%s\">\n", $resblockfile);
    }        
    
}




sub show_system ($$) {
    my $system_id = shift;
    my $query = shift;
    my $recall_url = $query->url(-relative=>1);
    my @planet_list;
    my $planet_info;


    @planet_list = get_planets_in_system ($system_id);




    if ( $#planet_list > 0 ) {
	my $planet;
	
	# Too many planets
	
	print $query->p("Select a planet: \n");
	print $query->start_ul();
	foreach  $planet ( @planet_list ) {
	    my $planet_id = $planet->{itemID};
	    my $planet_name = $planet->{itemName};
	    my $already = defined ($planet->{planetID}) ? "Already Have" : "Need";
	    print $query->li( "<a href=\"$recall_url?choose_planet=Choose&planet_id=$planet_id\">$planet_name ($already)</a>" );
	}
	print $query->end_ul();
	
    }

}

sub show_constellation ($$) {
    my $const_id = shift;
    my $query = shift;
    my $recall_url = $query->url(-relative=>1);



}    


# ---------------------------------------------

if ( 0 ) {
    print "<!--\n";
    printf (" Type = $planet_type\n Name = $planet_name\n Sec Stat = $secstat\n ");
    printf (" Submitted fields = %s\n ", join (", ", @names));
    print "-->\n";
}

if ( $#names < 0 ) {
    print $query->p("
Welcome to the E-Uni Abundance Project.  This webpage allows you to enter your observations 
of abundance for the various planets you have visited.



<h3>How to obtain an Estimate</h3>

<ol>
  <li>Bring up the star map, and right click on the desired star, and choose 'Show Info'.  Alternatively, you can type the 
system name into the search box and right click on the result to get Show Info.
  <li>Now choose the 'Orbital Bodies' tab. On each planet, note the type, and then right click and choose 'View In Planet
Mode'. 
   <li>Click on the Scan tab. You now have the abundances displayed.
   <li>Try to get a dark background, or the image analyzer will fail miserably.  (ie Zoom out so that the Build button and resource tabs are over space rather than a white planet.)
   <li>Next take a screenshot.
   <li>At this point, you can submit the screenshot below in the 'Snapshot File' field, or 
   <li>You can open it in an image editor such as <a href='http://greenshot.sourceforge.net/'>Greenshot</a>.
    <ul>
   <li>Measure off the number of pixels in each resource bar. (There are 135 in total, measure off the number of white ones.  You can just look at the beginning column number and the ending columns number rather than having to literally count the pixels.)  Please verify that your bars have 100 pixels, since in tests this held true for various resolutions tested, but needs wider testing.
   <li>Record the information below.
     </ul>
   <li> There also exist on-screen pixel rulers, such as KRuler which allow you to measure off the pixels on the screen.
</ol>

<p>

I believe I have an adaptable algorithm for detecting the location of the resource bars.  Please inform Shiu Juan in evemail if you find an example of it screwing up again.
<p>

The first step is to choose the planet you will be submitting.  You can either type the planet name, and 
values in directly below, or you can search for the planet in various ways.

<h3>Direct Entry</h3>


\n");


    #  Secstat J124504 (C6) = -0.99, Planets NULL, Sec-class NULL
    #  Secstat J235117 (C1) = -0.99, Planets NULL, Sec-class NULL
    

    print $query->start_form ();

    print table({-border=>undef},
		Tr({-align=>'LEFT',-valign=>'TOP'},
		   [
		    #td(['System' , $query->textfield(-name=>'system'), '']),
		    #td(['Planet Number' , $query->textfield(-name=>'planet_number'), '']),
		    #td(['Security Status' , $query->textfield(-name=> 'secstat'), '0.0-1.0, W1-6 for wormholes']),
		    td(['Planet Name', $query->textfield(-name => 'planet_name'), 'eg Aldrat V']),
		    #td(['Planet Type' , $query->popup_menu(-name=>'planet_type',
		#					   -values=>['Barren', 'Gas', 'Ice', 'Lava', 'Oceanic', 'Plasma', 
		#						     'Storm', 'Temperate']), '']),
		   # td (['Wormhole Class', $query->textfield(-name => 'wh_class'), 'eg C1, C5, etc']),

		    td(['Snapshot File' , $query->filefield(-name=> 'snapfile'), 'Submit a screenshot']),
		    td(['Resource 1' , $query->textfield(-name=> 'resource0'), '.. or fill in abundance values']),
		    td(['Resource 2' , $query->textfield(-name=> 'resource1'), '']),
		    td(['Resource 3' , $query->textfield(-name=> 'resource2'), '']),
		    td(['Resource 4' , $query->textfield(-name=> 'resource3'), '']),
		    td(['Resource 5' , $query->textfield(-name=> 'resource4'), '']),
		   ]
		)
	);
    print $query->hidden (-name => 'which_form', -default=>'direct_entry');
    print $query->submit(-name=>'Submit');

    print $query->end_form();

    print $query->hr . "\n";

    
    print $query->h3("Find a Planet") . "\n";
    print $query->start_form ();
    print $query->p("Planet Name: " .  $query->textfield(-name => 'planet_name') . $query->submit (-name=>"search", -value => "Find Planet"));
    print $query->end_form();

    print $query->hr;
    print $query->h3 ("Browse Regions");
    printf ("<a href=\"%s?list_regions=all\">Browse Regions</a>", $query->url(-relative=>1));

    print $query->hr;

    #print "NOTE: The wormhole entry is still a little messed up.  It is being worked on.<p>\n";

    print $query->h3 ("Data Dump");

    printf ("A first attempt at displaying statistics can be viewed <a href=\"abundance_stats.html\">Statistics View</a>.  I would love to hear from any bright web programmers that can think of a good layout or such.  The statistics available are : (Min, Max, Mean, StdDev, Variance, Sample Count).<p>");

    printf ("Until the analysis functions or Dump To Google Spreadsheet functions are working, please click <a href=\"abundance_dump.cgi\">Database Dump</a> for a .CSV file that you can bring into your spreadsheet or database program");
}
else {
    # They did submit something

    my $recall_url = $query->url(-relative=>1 );

    Abundance::Database::connect();


    my @resource_values = ();


=pod
    Potential Inputs:
      Submit button
         which_form=direct_entry
	     planet_name  or planet_id
	     snapfile
	     resource0, resource1, ... resource4

      Verify button
             planet_id
	     secstat
             planet_type
	     resource0, resource1, ... resource4

      search
         search="Find Planet"
             planet_name

	 search="system"
	     systemid

      choose_planet
         planet_id


      survey
         survey="constellation"
	    id

	 survey="region"
	    id

      list_regions
      

=cut
    

    printf ("<a href=\"%s\">Front Page</a>\n", $recall_url);


    if ( $query->param ('Submit') ) {
	my $which_form = $query->param ('which_form');

	if ( ( $which_form eq 'direct_entry') or 
	     ( $which_form eq 'show_planet') ) {

	    print $query->h3('Verify');



	    #my $system = $query->param ('system');
	    #my $planet_number = $query->param ('planet_number');
	    #my $secstat = $query->param ('secstat');
	    my $planet_name = $query->param('planet_name');
	    my $planet_type = $query->param ('planet_type');
	    my $planet_id = $query->param ('planet_id');
	    


	    my $planet_info;
	    my ($system, $systemName, $planet_number, $secstat, $wh_class, $show_secstat, $planet_type_id);


	    if ( defined $planet_id ) {
		$planet_info = planet_info_id ($planet_id);
	    }
	    if ( defined $planet_name ) {
		$planet_info = planet_info_name($planet_name);
	    }

	    
	    
	    if ( $planet_info ) {
		$system = $planet_info->{solarSystemID};
		$systemName = eve_id_to_name ($system);
		
		$planet_number = $planet_info->{celestialIndex};
		$wh_class = $planet_info->{wormholeClassID};
		$secstat = sprintf ("%.1f", $planet_info->{security});
		$show_secstat = (($wh_class <= 6) && ($wh_class >= 1) ) ? sprintf ("W%d", $wh_class) : $secstat;

		$planet_id = $planet_info->{itemID};
		$planet_name = $planet_info->{itemName};
		$planet_type = $planet_types {$planet_info->{typeID}};
		$planet_type_id = $planet_info->{typeID};
		
		$query->param ('system', $system);
		$query->param ('planet_number', $planet_number);
		$query->param ('secstat', $show_secstat);
		$query->param ('planet_type', $planet_type);
		
		
	    }
	    else {
		printf ("Unable find planet %s (%d), did you get the name right? <br />\n", $planet_name, $planet_id);
	    }
		    
	    # Extract stuff from an image
	
	    my $snap_fh = $query->upload ('snapfile');
	    my $resblockfile = undef;
	    my $resource_valuesref;
	    my $success = 0;
	    
	    if ( defined $snap_fh ) {
		printf ("<!-- snap_fh = %s $snap_fh --> <br />\n", $snap_fh);
		
		my $filename = $query->param('snapfile');
		my $tmpfilename = $query->tmpFileName($filename);
		
		if ( ref ($snap_fh ) ) {
		    printf ("<!-- snap_fh is ref %s --> <br />\n", ref ($snap_fh));
		    
		    #printf (" keys = %s <br />\n", join (", ", keys ( %{$snap_fh} ) ) );
		}
		
		if ( -r $tmpfilename ) {
		    printf ("<!--  can read tmpfile $tmpfilename --> <br />\n");
		}
		
		
		($success, $resblockfile, $resource_valuesref) = extract_image_file ($snap_fh, $system, $planet_number);

		@resource_values = @{$resource_valuesref};

		#my $success = $resource_values [5];
		

	    }
	    else {
		# They did not submit a file
		printf ("(No file submitted, using text fields)<br />\n");
	    }
	    
	    my @resource_vals_fields ;
	    
	    for ( my $i = 0; $i < 5; $i++ ) {
		$resource_vals_fields [$i] = $query->param ("resource$i");
	    }
	    

	    printf ("<!--  PlanName=$planet_name, Sys=$system, Num =$planet_number, Sec=$secstat, Type=$planet_type, vals=(%s) img=(%s)\n -->",   join (", ", @resource_vals_fields), join (", ", @resource_values));
	    
	    #printf (" def = %d (%s)\n ", defined %res_map, join (", ", keys (%res_map)));
	    
	    
	    my @resource_labels;
	    my $resname;
	    my @resource_stats;
	    
	    if ( defined $resources{$planet_type} ) {
		@resource_labels = @{$resources{$planet_type}->{res_map}};
	    }
	    else {
		@resource_labels = @{$resources{"Unknown"}->{res_map}};
	    }
	    
	    if ( $#resource_values < 4 ) {
		@resource_values = @resource_vals_fields;
	    }
	    
	    for ( my $i = 0; $i <= $#resource_values; $i++ ) {
		$query->param(-name => "resource$i", -value =>$resource_values[$i]) ;
		
		printf ("Setting %s to %s <br />\n", "resource$i", $query->param ("resource$i")) if $debug > 2;
		
	    }

	    
	    for (my $i=0; $i <= $#resource_labels; $i++) {
		my $resname = $resource_labels [$i];
		my $secstat = $query->param("secstat");
		my $secclass;
		my $rowhr;

		if ( $secstat =~ m/^W/ ) {
		    $secclass = "W";
		}
		elsif ( $secstat > 0.5 ) {
		    $secclass = "H";
		}
		elsif ( $secstat > 0.0 ) {
		    $secclass = "L";
		}
		else {
		    $secclass = "0";
		}


		
		if ( defined ($rowhr = stats_for ($planet_type_id, $secclass, $resname) ) ) {
		    $resource_stats[$i] = sprintf ("<div style=\"font-size:smaller\">%d-%d, avg %5.2f +/- %5.2f (%d samples)</div>", 
					    $rowhr->{min}, $rowhr->{max},
					    $rowhr->{mean}, $rowhr->{stddev}, 
					    $rowhr->{cnt});
		}	
		else {
		    $resource_stats[$i] = "";
		}
	    }
	    
	    
	    print $query->start_form ();
	    
	    print $query->hidden (-name => 'planet_id', -default=> $planet_id), 
	          $query->hidden(-name=> 'planet_type_id', -default=> $planet_type_id), 
	          $query->hidden(-name => 'planet_name', -default=> $planet_name) . "\n";
	    
	    print table({-border=>undef},
			Tr({-align=>'LEFT',-valign=>'TOP'},
			   [
			    td(['Planet Name', $planet_name, '']),
			    td(['System', $query->hidden (-name=>'system') . " " . $systemName, '']),
			    td(['Planet Number' , $query->textfield(-name=>'planet_number'), '']),
			    td(['Security Status' , $query->textfield(-name=> 'secstat'), '0.0-1.0, W1-6 for wormholes']),
			    #td(['Planet Type' , $query->popup_menu(-name=>'planet_type',
			#				       -values=>['Barren', 'Gas', 'Ice', 'Lava', 'Oceanic', 'Plasma', 
			#						 'Storm', 'Temperate']), '']),
			    td(['Planet Type', $planet_type, '']),
			    td([$resource_labels[0] , $query->textfield(-name=> 'resource0', -override=>0), $resource_stats[0]]),
			    td([$resource_labels[1] , $query->textfield(-name=> 'resource1'),  $resource_stats[1] ]),
			    td([$resource_labels[2] , $query->textfield(-name=> 'resource2'),  $resource_stats[2] ]),
			    td([$resource_labels[3] , $query->textfield(-name=> 'resource3'),  $resource_stats[3] ]),
			    td([$resource_labels[4] , $query->textfield(-name=> 'resource4'),  $resource_stats[4] ]),
			   ]
			)
		);
	    print "\n" . $query->submit(-name=>'Verify');
	    
	    print "\n" . $query->end_form();

	    if ( defined $resblockfile ) {
		printf ("<br /> <img src=\"%s\">\n", $resblockfile);
	    }
	    else {
		printf ("<br /> No image to display\n");
		
		
	    }
	}  # End if in direct_entry form
	else {
	    printf ("Unknown submission form");
	}

    }
    elsif ( $query->param ('Verify') ) {
	#  We are ready for final submission.   Save it.


	my @resource_vals_fields ;
	my $can_proceed  = 1;
	my ($planet_id, $planet_type_id, $systemid, $query_str);
	my ($remote_host, $remote_addr);
	my $recall_url;
	my $planet_info;
	my $wh_class;


	$planet_id = $query->param ('planet_id');
	$planet_type_id = $query->param ('planet_type_id');
	$planet_name = $query->param ('planet_name');
	$secstat = $query->param ('secstat');
	$systemid = $query->param ('system');

	if ( $secstat =~ m/W(\d)/ ) {
	    $wh_class = $1;
	}
	else {
	    $wh_class = undef;
	}


	$remote_host = $query->remote_host();
	$remote_addr = $query->remote_addr();


	my $resource_total = 0;
	my $count_0 = 0;
	my $count_100 = 0;
	for ( my $i = 0; $i < 5; $i++ ) {
	    $resource_vals_fields [$i] = $query->param ("resource$i");
	    $resource_total += $resource_vals_fields [$i];
	    if ( $resource_vals_fields [$i] == 0 ) {
		$count_0 ++;
	    }
	    if ( $resource_vals_fields [$i] > 99 ) {
		$count_100 ++;
	    }
	}

	my $planet_type = $query->param ('planet_type');

	if ( ( $resource_total < 40) or ($count_0 > 2) or ($count_100 > 2) ) {
	    $can_proceed = 0;
	    printf ("Rejecting implausible submission.   Please mail Shiu Juan with the planet name to fix parameters if this is correct.<br />");
	}
	
	# remote_addr not used

	if ( $#resource_values < 4 ) {
	    @resource_values = @resource_vals_fields;
	}
	
	#for ( my $i = 0; $i <= $#resource_values; $i++ ) {
	#    $query->param(-name => "resource$i", -value =>$resource_values[$i]) ;
	
	#    #printf ("Setting %s to %s <br />\n", "resource$i", $query->param ("resource$i"));
	#}


	save_planet ($planet_id, $remote_host, \@resource_values, 
		     $planet_type, $planet_type_id, $planet_name, $secstat, $wh_class);




	print $query->h3 ("Other Planets in this System");

	show_system($systemid, $query);

    }
    elsif  ($query->param ('search')  ) {
	my $recall_url = $query->url(-relative=>1 );
	my $planet_info;
	my ($system, $planet_number, $planet_id, $secstat, $wh_class, $show_secstat, $planet_type_id);
	my @planet_list = ();
	my $search_val = $query->param('search');

	#printf (" search val = (%s)\n", $search_val);


	if ( $search_val eq "Find Planet" ) {
	    $planet_name = $query->param ('planet_name');

	    @planet_list = query_planet_list_name ($planet_name);
	}
	elsif ($search_val eq 'system' ) {
	    my $systemid = $query->param ('systemid');

	    @planet_list = query_planet_list_system ($systemid);
	}


	if ( $#planet_list > 0 ) {
	    my $planet;

	    # Too many planets

	    print $query->p("Select a planet: \n");
	    print $query->start_ul();
	    foreach  $planet ( @planet_list ) {
		my $planet_id = $planet->{itemID};
		my $planet_name = $planet->{itemName};
		my $already = defined ($planet->{planetID}) ? "Already Have" : "Need";
		print $query->li( "<a href=\"$recall_url?choose_planet=Choose&planet_id=$planet_id\">$planet_name ($already)</a>" );
	    }
	    print $query->end_ul();
	    
	}
	elsif ( $#planet_list == 0 ) {

	    show_planet_form ($planet_info->{itemID}, $query);
	    
		$system = $planet_info->{solarSystemID};
		$planet_number = $planet_info->{celestialIndex};
		$wh_class = $planet_info->{wormholeClassID};
		$secstat = sprintf ("%.1f", $planet_info->{security});
		$show_secstat = (($wh_class <= 6) && ($wh_class >= 1) ) ? sprintf ("W%d", $wh_class) : $secstat;

		$planet_id = $planet_info->{itemID};
		
		
		$planet_type = $planet_types {$planet_info->{typeID}};
		$planet_type_id = $planet_info->{typeID};
		
		$query->param ('system', $system);
		$query->param ('planet_number', $planet_number);
		$query->param ('secstat', $show_secstat);
		$query->param ('planet_type', $planet_type);
		
		
	}
	else {
	    printf ("Unable find planet %s, did you get the name right? <br />\n", $planet_name);
	}    

    }
    elsif ( $query->param ('choose_planet') ) {
	show_planet_form ($query->param ('planet_id'), $query);
    }
    elsif ( $query->param ('survey') ) {
	my $what = $query->param ('survey');
	my $itemid = $query->param ('id');

	if ( $what eq 'constellation' ) {
	    my $hashref;
	    my @planet_hasharr;

	    print $query->h3 (sprintf ("Constellation %s", eve_id_to_name ($itemid)));

	    @planet_hasharr = query_planets_in_constellation ($itemid);



	    print $query->start_table ();
	    
	    print $query->Tr({-align=>'CENTER',-valign=>'TOP'}, 
			     [
			      $query->th(['System', '/Already Entered', '/Planets'])
			     ]) . "\n";

	    foreach $hashref (@planet_hasharr) {

		print $query->Tr ( 
		    $query->td( [ sprintf (
				      "<a href=\"$recall_url?search=system&systemid=%d\"> %s </a>",
				      $hashref->{solarSystemID}, $hashref->{solarSystemName}),
				  $hashref->{enteredCount}, $hashref->{planetCount} ] )
		    );
	    }

	    print $query->end_table ();
	}
	elsif ( $what eq 'region' ) {
	    my $hashref;
	    my @const_hasharr;

	    print $query->h3 (sprintf ("Region %s", eve_id_to_name ($itemid)));


	    @const_hasharr = query_constellations_in_region ($itemid);

	    print $query->start_table ();
	    
	    print $query->Tr({-align=>'CENTER',-valign=>'TOP'}, 
			     [
			      $query->th(['Constellation', '/Already Entered', '/Planets'])
			     ]) . "\n";

	    foreach $hashref ( @const_hasharr ) {
		print $query->Tr ( 
		    $query->td( [ sprintf ("<a href=\"$recall_url?survey=constellation&id=%d\"> %s </a>", 
		     $hashref->{constellationID}, $hashref->{constellationName}),  
		     $hashref->{enteredCount}, $hashref->{planetCount} ] )
		    );
	    }

	    print $query->end_table ();
	}
    }
    elsif ( $query->param('list_regions') ) {
	my %regions = list_regions ();
	my $region_name;

	foreach $region_name (sort keys %regions ) {
	    printf ( "<a href=\"$recall_url?survey=region&id=%d\"> %s </a> <br />\n", 
		     $region_name, $regions{$region_name});
	}
    }
    else {
	print "Unrecognized Submit Type<br />\n";

	print "Your submission: <pre>\n";
	foreach my $name ( @names ) {
	    printf (" F(%s) = %s\n", $name, $query->param($name));
	}
	print "</pre>\n";
    }

}



print $query->end_html ();
