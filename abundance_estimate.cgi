#!/usr/bin/perl 

use CGI qw(:standard);
use CGI::Carp qw/fatalsToBrowser/;
use Image::Magick;
use IO::Handle;
use DBI;
use POSIX;
use strict;
#use warnings;


$CGI::POST_MAX=1024 * 2000;  # max 100K posts


my $debug  = 1;


my $img_base = 'http://wiki.eveuniversity.org/w/images';

my %resources = ( 
    'Barren' => { res_map =>  [ 'Aqueous Liquids', 'Base Metals', 'Carbon Compounds', 'Micro Organisms', 'Noble Metals' ],
		  typeid => 2016, img=>'9/94/BarrenLarge.png' },
    'Gas' =>  { res_map => [ 'Aqueous Liquids', 'Base Metals', 'Ionic Solutions', 'Noble Gas', 'Reactive Gas' ],
		typeid => 13, img => '8/82/GasLarge.png' },
    'Ice' => { res_map => [ 'Aqueous Liquids', 'Heavy Metals', 'Micro Organisms', 'Noble Gas', 'Planktic Colonies' ] ,
	       typeid => 12, img => 'a/a3/IceLarge.png' },
    'Lava' => { res_map => [ 'Base Metals', 'Felsic Magma', 'Heavy Metals',  'Non-CS Crystals', 'Suspended Plasma' ] ,
	       typeid => 2015, img => 'b/b7/LavaLarge.png'},
    'Oceanic' => { res_map => [ 'Aqueous Liquids', 'Carbon Compounds', 'Complex Organisms', 'Micro Organisms', 'Planktic Colonies' ] ,
	       typeid => 2014, img=> '9/9e/OceanicLarge.png' },
    'Plasma' => { res_map => [ 'Base Metals', 'Heavy Metals', 'Noble Metals', 'Non-CS Crystals', 'Suspended Plasma' ],
	       typeid => 2063, img=> '2/29/PlasmaLarge.png' },
    'Storm' => { res_map => [ 'Aqueous Liquids', 'Base Metals', 'Ionic Solutions',  'Noble Gas', 'Suspended Plasma' ],
	       typeid => 2017, img => '7/78/StormLarge.png' },
    'Temperate' => { res_map => [ 'Aqueous Liquids', 'Autotrophs', 'Carbon Compounds', 'Complex Organisms', 'Micro Organisms' ],
	       typeid => 11, img=> 'a/a6/TemperateLarge.png' },
    'Shattered' => { res_map => [ 'R1', 'R2', 'R3', 'R4', 'R5' ] ,
	       typeid => 30889, img => '' },
    'Unknown' => { res_map => [ 'Resource 1', 'Resource 2', 'Resource 3', 'Resource 4', 'Resource 5' ], typeid => 999999, img => '' }
		    
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



my $find_planetname_sth;
my $find_planetid_sth;
my $search_planet_sth;
my $system_planets_sth;
my $eveid_to_name_sth;
my $current_abundance_sth;
my $const_planets_sth;
my $wh_class_sth;
my $region_consts_sth;
my $regionlist_sth;
my $stats_sth;

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


# -----------------
#   Utility Functions


#my $fuzzy_colour_factor = 5;
my $fuzzy_colour_factor = 12.0/256.0;
my $imagedir = "resourceblock";


sub fuzzy_arr_cmp ( $$$ ) {
    my ( $arr1, $arr2, $tolerance ) = @_;
    my @arr1 = @{ $arr1 };
    my @arr2 = @{ $arr2 };
    my $ret = -1;

    printf ("    arr_cmp  (%s) <=> (%s)\n", join (", ", @arr1), join (", ", @arr2)) if ($debug > 3);

    for ( my $i = 0; $i <= $#arr1; $i++ ) {
	my $diff =  $arr1[$i] - $arr2[$i];

	printf ("  fuz_arr_cmp [$i] (%f) ?= (%f) = $diff (\@ $tolerance)\n", $arr1[$i], $arr2[$i]) if ($debug > 3);
	if ( abs ($diff) > $tolerance ) {
	    printf ("   ... failed\n") if ($debug > 3);
	    return $diff;
	}
    }

    return 0;
}


sub arr_cmp ( $$ ) {
    my ( $a, $b ) = @_;
    return fuzzy_arr_cmp ($a, $b, 0);
}


sub round ($) {
    my $input = shift;
    my $remain = $input - floor ($input);

    if ( $remain >= 0.5) {
	return (ceil ( $input));
    }
    else {
	return (floor ( $input));
    }
}


my $want_width = 300;
my $want_height = 256;
my $top = 155;

my $space_top = 141;
my $docked_top = 155;   #  170 with a 3 line Docked In.
my $docked3_top = 170;
my $docked_autopilot_top = 240;
my $space_autopilot_top = 216;

#  Scenario is:
#    1, 2, 3 lines of Space/Docked In text (141,155,170)
#  + 76 rows if autopilot in use.

my $base_top = 141;
my $dist_top_to_build = 44;
my @top_list = ();



# The top of the block is somewhere between 155 and 219.

sub extract_image ( $ ) {
    my $image = shift;
    

    my ($width, $height) = $image->Get ('columns', 'rows');

    my $test_row = $top + 44;  # 199;  # 264; # 221

    #  Constants determined empirically on 1280x1024
    my $res_row_height = 24;   # How tall is a resource line
    my $first_res_row = 142;   # How far down from (0,0) of the cropped image is the first resource line
    my $resource_width = 135;  # How many columns in a resource line
    my $top_to_build_dist = 44;  # How far from the top of the block to the Build button top.
    my $dock_rows = 14;   # Each line of "Docked in" is another 14 rows
    my $auto_rows = 76;   # The autopilot adds another 76 rows
    
    my $cur_col = 1;

    my $edge_image = $image->Clone();
    
    #my $debug = 5;
    #  Look for the EXIT button

    my $found = 0;
    my $count_line_pixels = 0;
    #my $want_line_length = 311 - 272;  # This the length of the Exit button
    my $want_line_length = 284-156;  # This the length of the Build button
    $want_line_length -= 4;  # The edging takes a dip just on the other side of the vertical line.
    my $line_start = -1;


=pod Test Data
Lumin sequence:
   59:(0,0,0)  60:(0.3765, 0.4039, 0.4353) 61:(0.2118, 0.2275, 0.2471) 62:(0.2118, 0.2275, 0.2471) ... 187:(0.2118, 0.2275, 0.2471) 188:(0.4706, 0.5059, 0.5451) 189:(0.3412, 0.3686, 0.3961) 190:(0.3412, 0.3686, 0.3961) end of whole sequence is 280.
(0.211764705882353, 0.227450980392157, 0.247058823529412)  - Lum III  seg end (0.470588235294118, 0.505882352941177, 0.545098039215686)

Algo Seq:
  59:(0,0,0) 60: (0.4196, 0.4039, 0.3922) 61: (0.2353, 0.2275, 0.2196) 188:(0.5294, 0.5020, 0.4863) 189: (0.3804, 0.3647, 0.3490) 
(0.235294117647059, 0.227450980392157, 0.219607843137255)  - Algo II  seg end  (0.529411764705882, 0.501960784313725, 0.486274509803922)
(0.231372549019608, 0.231372549019608, 0.23921568627451) - Bere I
(0.231372549019608, 0.231372549019608, 0.23921568627451) - Arnat 
(0.380392156862745, 0.384313725490196, 0.388235294117647) - Aldrat I
(0.352941176470588, 0.368627450980392, 0.372549019607843) - Eygfe I



=cut



    print "<pre>\n" if $debug > 1;

    if ( $debug > 2 ) {
	printf (" Image Info: size = (%d x %d) \n", $width, $height);
    }

    #$image->Display();

    $edge_image->Edge (radius=>1);

    #$edge_image->Display();

    # Look for the correct row.  It will be somewhere between 194 to 262
    my $dock_lines;
    my $auto_pilot;


 FIND_BUILD:
    for ( $dock_lines = 0; ( $dock_lines < 3) && ($found==0); $dock_lines++) {
	for ( $auto_pilot = 0; ($auto_pilot < 2) && ($found == 0); $auto_pilot++ ) {
	    $top = $base_top + ( $dock_lines * $dock_rows) + ( $auto_pilot * $auto_rows ) ;
	    $test_row = $top + $top_to_build_dist;


    for ( my $cur_col = 1; ($cur_col < 365) && ($found == 0); $cur_col++ ) {
	my @above_pixel = $edge_image->GetPixel (x=>$cur_col, y=>($test_row-1));
	my @pixels = $edge_image->GetPixel (x=>$cur_col, y=>$test_row);
	my @below_pixel = $edge_image->GetPixel (x=>$cur_col, y=>($test_row+1));
        my @diff_pixel;
	
	my @pixels256;
	
	for ( my $i = 0; $i < 3; $i++) {
	    $pixels256 [$i] = sprintf ("%d", $pixels[$i] * 256);
	}

	for ( my $i = 0; $i < 3; $i++) {
	    $diff_pixel [$i] = sprintf ( "%.4f", abs($pixels[$i] - $above_pixel[$i]));
	}

	
	printf ("(%3d, %3d)  above(%s)\n            targ (%s)\n            below(%s)  diff (%s)\n", 
		$cur_col, $test_row, join (", ", @above_pixel),
		join (", ", @pixels), join (", ", @below_pixel), join (", ", @diff_pixel)) if $debug > 3;

	my @want_pixels = (124.0/256.0, 130.0/256.0, 133.0/256.0);
	#my @want_pixels = (124, 130, 133);
	
	#  Try for betwene 0.2-0.6 ie 0.4 +/- 0.2
	my @want_contrast = (0.7, 0.7, 0.7);
	my $contrast_fuzz = 0.35;
	
	printf (" Comparing (%d, %d) = (%s) to (%s) (+/- %f) found=%d\n",  $cur_col, $test_row, join (", ", @pixels), join (", ", @want_pixels), $fuzzy_colour_factor, $count_line_pixels) if ($debug > 2);
	
	

	#if ( fuzzy_arr_cmp (\@pixels, \@want_pixels, $fuzzy_colour_factor) == 0 )  {
	if ( fuzzy_arr_cmp (\@diff_pixel, \@want_contrast, $contrast_fuzz) == 0 )  {
	    if ( $count_line_pixels == 0 ) {
		$line_start = $cur_col;
	    }
	    
	    $count_line_pixels++;
	    
	    if ( $count_line_pixels >= $want_line_length ) {
		$found = 1;
	    }
	}
	else {
	    # Came to the end of the line without enough pixels.
	    $count_line_pixels = 0;
	}
    }
	}  # End for auto_pilot lines or not
    }      # End for how many rows of "Docked in: " or "Nearest: "

    #  Debugging: force values to the test image:
    #$found = 1; $line_start = 272; 
    
    printf (" Found = %d, Line Start = %d, Line Pixels = %d\n", $found, $line_start, $count_line_pixels) if $debug > 2;
    
    #my $left  = $line_start - (272-49);
    my $left  = $line_start - (156-146);
    
    my $geo = sprintf ("%dx%d+%d+%d", $want_width, $want_height, $left, $top);
    
    printf ("Cropping ($width x $height) to  $geo into file-crop.png\n") if $debug > 3;
    my $x = $image->Crop (geometry=>"$geo");
    warn "$x" if "$x";
    
    $x = $image->Set( page=>'0x0+0+0' );


    my @resource_rows = (135, 160, 180, 205, 230);
    my @abundance_rows = (0,0,0,0,0);
    
    my $resource_col_start = 210-50;

    $resource_rows [0] = $first_res_row;
    for ( my $r = 1; $r <= 4; $r++) {
	$resource_rows[$r] = $resource_rows[$r-1] + $res_row_height;
    }
    
    
    for ( my $r = 0; $r <= $#resource_rows; $r++) {
	my $abundance = 0;
	
	for ( my $test_col = $resource_col_start; $test_col <= ($resource_col_start + $resource_width); $test_col++) {
	    my ($x, $y) = ($test_col, $resource_rows[$r] );
	    
	    my @pixels = $image->GetPixel (x=>$x, y=>$y);
	    
	    my @pixels256;
	    
	    for ( my $i = 0; $i < 3; $i++) {
		$pixels256 [$i] = sprintf ("%d", $pixels[$i] * 256);
	    }
	    
	    #my @want_pixels = (195,195,195);   # Lit portion is (199,199,199), unlit is (64,64,64)
	    #my @want_pixels = (195.0/256.0,195.0/256.0,195.0/256.0);   # Lit portion is (199,199,199), unlit is (64,64,64)
	    #my @want_pixels = (190.0/256.0,190.0/256.0,190.0/256.0);   # Lit portion is (199,199,199), unlit is (64,64,64), sometimes as low as 180 or high as 199.
	    my @want_pixels = (217.0/256.0,217.0/256.0,217.0/256.0);   # Lit portion is (199,199,199), unlit is (64,64,64), sometimes as low as 180 or high as 199.

	    #  Need more adaptation in lit vs unlit.   The color is now lit = 217,217,217.  unlit = 123,108,92 or 58,57,58 depending on whether it has a light background or dark background
	    
	    
	    printf (" R:Comparing (%d, %d) = (%s) to (%s) %d\n",  $x, $y, join (", ", @pixels), join (", ", @want_pixels), $count_line_pixels) if ($debug > 2);
	    
	    if ( fuzzy_arr_cmp (\@pixels, \@want_pixels, $fuzzy_colour_factor) == 0 )  {	
		my @mark_pixels = @pixels;
		$mark_pixels [0] = 0.68; $mark_pixels [1] = $mark_pixels [2] = 0.11;

		@mark_pixels = ( 0.68, 0.11, 0.11 );
		
		$abundance++;
		$image->SetPixel (x=>$x, y=>$y, channel=>"RGB", color=>\@mark_pixels);
	    }
	    else {
		my @mark_pixels = @pixels;
		
		$mark_pixels [2] = 0.68; $mark_pixels [0] = $mark_pixels [1] = 0.11;

		@mark_pixels = ( 0.11, 0.11, 0.68 );
		
		$image->SetPixel (x=>$x, y=>$y, color=>\@mark_pixels);
	    }
	}
	
        #  Scale to the total width of the resource bar.
	$abundance_rows [$r]  = round ($abundance * 100.0/$resource_width);
    }
    
=pod
    $x = $image->Write ("$file-crop.png");
    warn "$x" if "$x";
=cut
    
    if ( $debug > 3 ) {
	printf ("Abundances:\n");
	for ( my $r = 0; $r <= $#abundance_rows; $r++) {
	    printf ("   Resource %d = %d\n", $r, $abundance_rows[$r]);
	}
    }

    print "</pre>\n" if $debug > 1;

    
    return ( @abundance_rows, 1 );

}



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

sub show_planet_form ($$) {
    my $planet_id = shift;
    my $query = shift;

    my @resource_vals_fields;
    my @resource_values;
    
    my $recall_url = $query->url (-relative=>1);

    $find_planetid_sth->execute ($planet_id);
    my $planet_info;
    my ($systemid, $systemname, $planet_number, $secstat, $wh_class, $show_secstat, $planet_type_id);

    my $resblockfile;
    my $image;
    my $planet_name_w_img;

    
    if ( $planet_info = $find_planetid_sth->fetchrow_hashref() )  {
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


    $system_planets_sth->execute ($system_id);
    while ( $planet_info = $system_planets_sth->fetchrow_hashref() )  {
	push (@planet_list , $planet_info);
    }
    
    $system_planets_sth -> finish ();
    



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
    my $find_planet_sql;


    #  Connect to database
    $dbh = DBI->connect($dsn,$dbuser,$dbpass);

    $find_planet_sql = "SELECT itemID, m.typeID, solarSystemID, constellationID, regionID, celestialIndex, itemName, security, wormholeClassID, celestialIndex, typeName, graphicID from mapDenormalize m JOIN invTypes t ON m.typeID = t.typeID LEFT JOIN mapLocationWormholeClasses c ON m.regionID = c.locationID";
    
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

	    

	    my $planet_info;
	    my ($system, $systemName, $planet_number, $secstat, $wh_class, $show_secstat, $planet_type_id);


	    if ( defined $planet_id ) {
		$find_planetid_sth->execute($planet_id);
		$planet_info = $find_planetid_sth->fetchrow_hashref();
	    }
	    if ( defined $planet_name ) {
		$find_planetname_sth->execute ($planet_name);
		$planet_info = $find_planetname_sth->fetchrow_hashref() ;
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
		    

	
	    my $snap_fh = $query->upload ('snapfile');
	    my $resblockfile = undef;
	    
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
		
		
		my $image = Image::Magick->new ();
		
		#my $io_handle = $snap_fh->handle;
		#$image->Read(file=>\*{$io_handle});
		
		
		my $x = $image->Read(file=>\*{$snap_fh});
		warn "$x" if "$x";
		
		#  We could $image_resblock = $image->Clone(); if we had a use for the original
		
		@resource_values = extract_image ( $image );
		
		my $success = $resource_values [5];
		
		if ( $success ) {
		    $resblockfile = sprintf ("%s/%s-%s-resblock.png", $imagedir, $system, $planet_number);
		    
		    $x = $image->Write ($resblockfile);
		    warn "$x" if "$x";
		    
		    #print "Wrote out resource-crop.png ($width x $height) <img src=resource-crop.png>\n" if $debug > 5;
		}
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

		$stats_sth->execute ($planet_type_id, $secclass, $resname);
		
		if ( defined ($rowhr = $stats_sth->fetchrow_hashref () ) ) {
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
	my @resource_fields = ('resource0', 'resource1', 'resource2', 'resource3', 'resource4');
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
	

	my @resource_labels;

	if ( defined $resources{$planet_type} ) {
	    @resource_labels = @{$resources{$planet_type}->{res_map}};

	    for ( my $i = 0; $i <= $#resource_labels; $i++) {
		$resource_fields[$i] = $resource_col_names {$resource_labels[$i]};
	    }
	}
	else {
	    my $found = 0;
	    #  Try looking up the planet again
	    $find_planetid_sth->execute ( $planet_id );

	    if ( $planet_info = $find_planetid_sth->fetchrow_hashref() )  {
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

	if ( $#resource_values < 4 ) {
	    @resource_values = @resource_vals_fields;
	}

	#for ( my $i = 0; $i <= $#resource_values; $i++ ) {
	#    $query->param(-name => "resource$i", -value =>$resource_values[$i]) ;

	#    #printf ("Setting %s to %s <br />\n", "resource$i", $query->param ("resource$i"));
	#}


	if ( ! defined $planet_type_id  ) {
	    $planet_type_id = $resources{$planet_type}->{typeid};
	}


	#printf ("<pre> PlanName=$planet_name, Sys=$system, Num =$planet_number, Sec=$secstat, Type=$planet_type, vals=(%s) \n</pre>",   join (", ", @resource_vals_fields));

	#printf (" def = %d (%s)\n ", defined %res_map, join (", ", keys (%res_map)));


	# Build the insert query
	$query_str = sprintf ("INSERT INTO planetAbundance (planetID, planetType, planetName, securityStatus, wh_class, submit_from, submit_date, resource0, resource1, resource2, resource3, resource4, %s, %s, %s, %s, %s) VALUES (%d, %d, '%s', '%s', '%s', '%s', now(), %d, %d, %d, %d, %d, %d, %d, %d, %d, %d )", @resource_fields, $planet_id, $planet_type_id, $planet_name, $secstat, $wh_class, $remote_host, @resource_values, @resource_values );

	printf ("<!-- SQL stmt = %s -->\n", $query_str);

	my $row_count = $dbh->do ($query_str);
	printf ("<!-- Rows Affected = %d  -->\n", $row_count);
	if ( $dbh->errstr () ) {
	    printf ("Error = %s\n", $dbh->errstr());
	}


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
	    $search_planet_sth->execute ($planet_name) or die "Failure exec search_planet_sth: " . $dbh->errstr;

	    
	    while ( $planet_info = $search_planet_sth->fetchrow_hashref() )  {
		push (@planet_list , $planet_info);
	    }

	    $search_planet_sth -> finish ();
	}
	elsif ($search_val eq 'system' ) {
	    my $systemid = $query->param ('systemid');

	    $system_planets_sth->execute ($systemid);
	    while ( $planet_info = $system_planets_sth->fetchrow_hashref() )  {
		push (@planet_list , $planet_info);
	    }

	    $system_planets_sth -> finish ();

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

	    print $query->h3 (sprintf ("Constellation %s", eve_id_to_name ($itemid)));

	    $const_planets_sth->execute ($itemid) or die "Failure exec const_planets_sth: " . $dbh->errstr;


	    print $query->start_table ();
	    
	    print $query->Tr({-align=>'CENTER',-valign=>'TOP'}, 
			     [
			      $query->th(['System', '/Already Entered', '/Planets'])
			     ]) . "\n";

	    while ( $hashref = $const_planets_sth->fetchrow_hashref() )  {
		print $query->Tr ( 
		    $query->td( [ sprintf (
				      "<a href=\"$recall_url?search=system&systemid=%d\"> %s </a>",
				      $hashref->{solarSystemID}, $hashref->{solarSystemName}),
				  $hashref->{enteredCount}, $hashref->{planetCount} ] )
		    );
	    }

	    print $query->end_table ();


	
	    $const_planets_sth -> finish ();	
	    


	}
	elsif ( $what eq 'region' ) {
	    my $hashref;

	    print $query->h3 (sprintf ("Region %s", eve_id_to_name ($itemid)));


	    $region_consts_sth->execute ($itemid) or die "Failure exec region_consts_sth: " . $dbh->errstr;

	    print $query->start_table ();
	    
	    print $query->Tr({-align=>'CENTER',-valign=>'TOP'}, 
			     [
			      $query->th(['Constellation', '/Already Entered', '/Planets'])
			     ]) . "\n";

	    while ( $hashref = $region_consts_sth->fetchrow_hashref() )  {
		print $query->Tr ( 
		    $query->td( [ sprintf ("<a href=\"$recall_url?survey=constellation&id=%d\"> %s </a>", 
		     $hashref->{constellationID}, $hashref->{constellationName}),  
		     $hashref->{enteredCount}, $hashref->{planetCount} ] )
		    );
	    }

	    print $query->end_table ();

	    
	    $region_consts_sth -> finish ();	

	}
    }
    elsif ( $query->param('list_regions') ) {
	my $hashref;

	$regionlist_sth->execute () or die "Failure exec regionlist_sth: " . $dbh->errstr;

	while ( $hashref = $regionlist_sth->fetchrow_hashref() )  {
	    printf ( "<a href=\"$recall_url?survey=region&id=%d\"> %s </a> <br />\n", $hashref->{regionID}, $hashref->{regionName});
	}
	
	$regionlist_sth -> finish ();	
	
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
