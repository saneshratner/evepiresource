#!/usr/bin/perl 

# ====== abundance_include.pl =============


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



my $dsn = "DBI:mysql:database=db_euni;host=mysql.isp.net";
my $dbuser = "eveuser";
my $dbpass = "password";

# ====== abundance_include.pl ============= end

1;
