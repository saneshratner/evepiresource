#!/usr/bin/perl -w


use strict;

package Abundance::Image;

use POSIX;

use base 'Exporter';
our @EXPORT_OK = qw (fuzzy_arr_cmp arr_cmp round extract_image extract_image_file);


use Abundance::Config;

use Image::Magick;


my $debug = $Abundance::Config::debug_level;
my $have_display = $Abundance::Config::have_display;

# -----------------
#   Utility Functions


#my $fuzzy_colour_factor = 5;
my $fuzzy_colour_factor = 12.0/256.0;
my $imagedir = $Abundance::Config::imagedir;


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


# We are cutting out a square from 8 pixels above the planet symbol and planet name
#  which starts [2015-May] at row 158 or 99 depending on how much of the current location/docked
#  station is displayed, 
#    and depending on the location of the Neocom, at column 16 or 48. 
#  It is $want_height tall and $want_width wide, and should include
#  out to the X for closing to view, and the "No Filter" bar.
#
# We are going to detect scale bar which starts 
#   Y: 55 pixels below our crop-point (100+55=155 or 158+55=213), and 
#   X: between 48-78 from the edge, or 32 pixels from the crop-point.


#my $base_top = 141;
my $base_top = 100;
#my $base_top =  140;
#my $base_top =  142;
#my $dist_top_to_build = 44;
my $dist_top_to_build = 55;   # Actually to Scale
my $scale_start = 32;
my @top_list = ();



# The top of the block is somewhere between 155 and 219.

sub extract_image ( $ ) {
    my $image = shift;

    my $debugfilebase = "resourceblock/tempimage";
    my $tmpfile;
    

    my ($width, $height) = $image->Get ('columns', 'rows');

    my $test_row = $top + 44;  # 199;  # 264; # 221

    #  Constants determined empirically on 1280x1024
    my $res_row_height = 24;   # How tall is a resource line
    my $first_res_row = 118;   # How far down from (0,0) of the cropped image is the first resource line
    my $resource_width = 135;  # How many columns in a resource line
    #my $top_to_build_dist = 44;  # How far from the top of the block to the Build button top.
    my $top_to_build_dist = 55;  # How far from the top of the block to the Scale row.
    #my $dock_rows = 14;   # Each line of "Docked in" is another 14 rows
    my $dock_rows = 58;   # The current location block is 58 tall.
    my $auto_rows = 76;   # The autopilot adds another 76 rows
    
    my $cur_col = 1;

    my $edge_image = $image->Clone();

    
    
    #my $debug = 5;
    #  Look for the EXIT button

    my $found = 0;
    my $count_line_pixels = 0;
    #my $want_line_length = 311 - 272;  # This the length of the Exit button
    #my $want_line_length = 284-156;  # This the length of the Build button
    my $want_line_length = 206-73;  # This the length of the Build button
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

    if ( $have_display && ( $debug > 3 ) ) {
	#$image->Display();
    }

    $edge_image->Edge (radius=>1);

    if ( $debug > 3 ) {
	$tmpfile = sprintf ("%s-edge.png", $debugfilebase);
	$edge_image->Write (filename => $tmpfile);
    }

    if ( $have_display && ( $debug > 3 ) ) {
	$edge_image->Display();

	if (0) {
	printf (STDERR "Preview EdgeDetect\n");
	my $preview = $image->Preview ('EdgeDetect');
	$preview->Display();

	printf (STDERR "Preview Sharpen\n");
	$preview = $image->Preview ('Sharpen');
	$preview->Display();

	printf (STDERR "Preview ReduceNoise\n");
	$preview = $image->Preview ('ReduceNoise');
	$preview->Display();
	}
    }




    # Look for the correct row.  It will be somewhere between 194 to 262
    my $dock_lines;
    my $auto_pilot;


 FIND_BUILD:  # Actually finding Scale now.
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
    #my $left  = $line_start - (156-146);
    my $left = $line_start - $scale_start;
    
    my $geo = sprintf ("%dx%d+%d+%d", $want_width, $want_height, $left, $top);
    
    printf ("Cropping ($width x $height) to  $geo into file-crop.png\n") if $debug > 3;
    my $x = $image->Crop (geometry=>"$geo");
    warn "$x" if "$x";
    
    $x = $image->Set( page=>'0x0+0+0' );

    if ( $debug > 3 ) {
	$x = $image->Write (filename => "$debugfilebase-crop.png");
	warn "$x" if "$x";
    }

    #my @resource_rows = (135, 160, 180, 205, 230);
    my @resource_rows = (118, 142, 166, 190, 215);
    my @abundance_rows = (0,0,0,0,0);
    
    #my $resource_col_start = 210-50;
    my $resource_col_start = 178;

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

}   # End extract_image


sub extract_image_file ($$$) {
    my ($snap_fh, $system, $planet_number) = @_;
    my ( $success, $resblockfile, @resource_values);
    
    my $write_orig = $Abundance::Config::write_orig;

    my $image = Image::Magick->new ();
    
    #my $io_handle = $snap_fh->handle;
    #$image->Read(file=>\*{$io_handle});
    
    my $snap_type = ref ( $snap_fh );
    my $x;

    if ( $snap_type eq "IO" ) {
	$x = $image->Read(file=>\*{$snap_fh});
    }
    else {
	#  It is not a reference, likely passed a _FILENAME_
	$x = $image->Read(file=>$snap_fh);	
    }

    warn "$x" if "$x";
    
    #  We could $image_resblock = $image->Clone(); if we had a use for the original

    if ( $write_orig > 0 ) {
	$resblockfile = sprintf ("%s/%s-%s-orig.png", $imagedir, $system, $planet_number);
	
	$x = $image->Write ($resblockfile);
	warn "$x" if "$x";
    }
    
    @resource_values = extract_image ( $image );
		
    $success = $resource_values [5];

    if ( $success ) {
	$resblockfile = sprintf ("%s/%s-%s-resblock.png", $imagedir, $system, $planet_number);
	
	$x = $image->Write ($resblockfile);
	warn "$x" if "$x";
	
	#print "Wrote out resource-crop.png ($width x $height) <img src=resource-crop.png>\n" if $debug > 5;
    }
    

    return ($success, $resblockfile, \@resource_values);

}



1;
