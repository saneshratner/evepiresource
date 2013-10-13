#!/usr/bin/perl -w


use Image::Magick;
use POSIX;
use strict;


my $debug = 4;

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

my $want_width = 300;
my $want_height = 256;
my $top = 220;


sub extract_image ( $ ) {
    my $image = shift;
    

    my ($width, $height) = $image->Get ('columns', 'rows');

    my $test_row = 264; # 221
    
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

    $image->Display();

    $edge_image->Edge (radius=>1);

    $edge_image->Display();
    $edge_image->Write ("edgeimage.png");

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
		join (", ", @pixels), join (", ", @below_pixel), join (", ", @diff_pixel));

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


    #  Debugging: force values to the test image:
    #$found = 1; $line_start = 272; 
    
    printf (" Found = %d, Line Start = %d, Line Pixels = %d\n", $found, $line_start, $count_line_pixels) if $debug > 3;
    
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
    my $resource_width = 100;
    
    for ( my $r = 0; $r <= $#resource_rows; $r++) {
	my $abundance = 0;
	
	for ( my $test_col = $resource_col_start; $test_col < ($resource_col_start + $resource_width); $test_col++) {
	    my ($x, $y) = ($test_col, $resource_rows[$r] );
	    
	    my @pixels = $image->GetPixel (x=>$x, y=>$y);
	    
	    my @pixels256;
	    
	    for ( my $i = 0; $i < 3; $i++) {
		$pixels256 [$i] = sprintf ("%d", $pixels[$i] * 256);
	    }
	    
	    #my @want_pixels = (195,195,195);   # Lit portion is (199,199,199), unlit is (64,64,64)
	    my @want_pixels = (190.0/256.0,190.0/256.0,190.0/256.0);   # Lit portion is (199,199,199), unlit is (64,64,64)
	    #my @want_pixels = (195.0/256.0,195.0/256.0,195.0/256.0);   # Lit portion is (199,199,199), unlit is (64,64,64)
	    
	    
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
	
	$abundance_rows [$r]  = $abundance;
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




my $image = Image::Magick->new ();

my $file = shift @ARGV;
	    
my $x;

if ( ! defined $file) {
    exit (1);
}


$x = $image ->Read ($file);
warn "$x" if "$x";

my $top_perc = 6.0/27.0;
my $bot_perc = 12.5/27.0;
my $left_perc = 1.0/43.0;
my $width_perc = 7.5/43.0;



my ($width, $height) = $image->Get ('columns', 'rows');

#my $top = $height * $top_perc;
my $bot = $height * $bot_perc;
#my $want_height = $bot - $top;

#my $want_width =  $width * $width_perc;
my $left  = $width * $left_perc;

$want_width = 300;
$want_height = 256;
$left = 40;
$top = 220;

my $test_row = 221;
#my $fuzzy_colour_factor = 10;



=pod


$cur_col = 1;

#  Look for the home button

$found = 0;
$count_line_pixels = 0;
$want_line_length = 363 - 324;  # This the length of the Home button
$line_start = -1;



for ( $cur_col = 1; ($cur_col < 365) && ($found == 0); $cur_col++ ) {
    @pixels = $image->GetPixel (x=>$cur_col, y=>$test_row);

    my @pixels256;

    for ( my $i = 0; $i < 3; $i++) {
        $pixels256 [$i] = sprintf ("%d", $pixels[$i] * 256);
    }
    
    #my @want_pixels = (124.0/256.0, 130.0/256.0, 133.0/256.0);
    my @want_pixels = (124, 130, 133);
    

    printf (" Comparing (%d, %d) = (%s) to (%s) %d\n",  $cur_col, $test_row, join (", ", @pixels256), join (", ", @want_pixels), $count_line_pixels) if ($debug > 2);

    if ( fuzzy_arr_cmp (\@pixels256, \@want_pixels, $fuzzy_colour_factor) == 0 )  {
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

printf (" Found = %d, Line Start = %d, Line Pixels = %d\n", $found, $line_start, $count_line_pixels);

$left  = $line_start - (324-140);

my $geo = sprintf ("%dx%d+%d+%d", $want_width, $want_height, $left, $top);

printf ("Cropping ($width x $height) to  $geo into $file-crop.png\n");
$x = $image->Crop (geometry=>"$geo");
warn "$x" if "$x";

$x = $image->Set( page=>'0x0+0+0' );

my @resource_rows = (135, 160, 180, 205, 230);
my @abundance_rows = (0,0,0,0,0);

my $resource_col_start = 166;
my $resource_width = 100;

for ( my $r = 0; $r <= $#resource_rows; $r++) {
    my $abundance = 0;

    for ( my $test_col = $resource_col_start; $test_col < ($resource_col_start + $resource_width); $test_col++) {
	my ($x, $y) = ($test_col, $resource_rows[$r] );
	
	my @pixels = $image->GetPixel (x=>$x, y=>$y);
	
        my @pixels256;
	
	for ( my $i = 0; $i < 3; $i++) {
	    $pixels256 [$i] = sprintf ("%d", $pixels[$i] * 256);
	}
	
	my @want_pixels = (195,195,195);   # Lit portion is (199,199,199), unlit is (64,64,64)
	
	
	printf (" R:Comparing (%d, %d) = (%s) to (%s) %d\n",  $x, $y, join (", ", @pixels256), join (", ", @want_pixels), $count_line_pixels) if ($debug > 2);
	
	if ( fuzzy_arr_cmp (\@pixels256, \@want_pixels, $fuzzy_colour_factor) == 0 )  {	
	    my @mark_pixels = @pixels;

	    $mark_pixels [0] = 0.68; $mark_pixels [1] = $mark_pixels [2] = 0.11;

	    $abundance++;
	    $image->SetPixel (x=>$x, y=>$y, color=>\@mark_pixels);
	}
        else {
	    my @mark_pixels = @pixels;

	    $mark_pixels [1] = 0.68; $mark_pixels [0] = $mark_pixels [2] = 0.11;

	    $image->SetPixel (x=>$x, y=>$y, color=>\@mark_pixels);
	}
    }

    $abundance_rows [$r]  = $abundance;
}


$x = $image->Write ("$file-crop.png");
warn "$x" if "$x";


=cut

	    #$imagedir = ".";
	    my $system = "Unknown"; my $planet_number=5;

my @abundance_rows = extract_image ($image);

	    my $resblockfile = sprintf ("%s/%s-%s-resblock.png", $imagedir, $system, $planet_number);
	    
	    $x = $image->Write ($resblockfile);
	    warn "$x" if "$x";

		$image->Display();
			      
printf ("Abundances:\n");
for ( my $r = 0; $r <= $#abundance_rows; $r++) {
    printf ("   Resource %d = %d\n", $r, $abundance_rows[$r]);
}
