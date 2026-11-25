// RT-1650HX "Merlin-Hex" 4-Stack Coaxial Sawtooth Propulsion Unit
// Units: millimeters (mm)

$fn = 96;

// --- Parametric Dimensions ---
stack_count        = 4;
stack_length       = 145;    // Axial length per sawtooth module
stack_gap          = 12;     // Inter-stack cooling & phase bus gap
stator_outer_d     = 540;    // Fits inside P-51 cowling contour
stator_inner_d     = 340;
rotor_outer_d      = 336;    // 2.0 mm radial air gap
shaft_d            = 110;    // Hollow high-tensile steel prop shaft
shaft_bore_d       = 55;     // Hydraulic/electric prop-pitch actuator bore
sawtooth_poles     = 48;     // High-pole-count low-RPM torque profile
tooth_depth        = 14;
jacket_thickness   = 18;
thrust_collar_len  = 110;

total_core_len = stack_count * stack_length + (stack_count - 1) * stack_gap;

module sawtooth_ring(outer_r, inner_r, teeth, depth, height) {
    linear_extrude(height = height) {
        difference() {
            polygon(points = [
                for (i = [0 : teeth * 2 - 1])
                    let(
                        angle = i * 360 / (teeth * 2),
                        // Asymmetric sawtooth profile for directional high-torque bias
                        r = (i % 2 == 0) ? outer_r : (outer_r - depth),
                        a_shift = (i % 2 == 0) ? 0 : (360 / (teeth * 4))
                    )
                    [r * cos(angle + a_shift), r * sin(angle + a_shift)]
            ]);
            circle(r = inner_r);
        }
    }
}

module motor_stack_module() {
    union() {
        // Outer Stator Core & Cooling Jacket
        difference() {
            cylinder(d = stator_outer_d + jacket_thickness * 2, h = stack_length);
            translate([0, 0, -1])
                cylinder(d = stator_inner_d, h = stack_length + 2);
            // Helical-style glycol cooling manifold groove
            translate([0, 0, stack_length * 0.2])
                difference() {
                    cylinder(d = stator_outer_d + jacket_thickness, h = stack_length * 0.6);
                    translate([0, 0, -1])
                        cylinder(d = stator_outer_d + 4, h = stack_length * 0.6 + 2);
                }
        }
        // Sawtooth Rotor Core
        color("SteelBlue")
            sawtooth_ring(rotor_outer_d / 2, shaft_d / 2, sawtooth_poles, tooth_depth, stack_length);
    }
}

module thrust_bearing_nose() {
    // Forward tapered housing absorbing propeller thrust load
    color("DarkSlateGray")
    difference() {
        cylinder(d1 = stator_outer_d * 0.78, d2 = 240, h = thrust_collar_len);
        translate([0, 0, -1])
            cylinder(d = shaft_d + 16, h = thrust_collar_len + 2);
    }
}

module mounting_lugs() {
    // 4-point engine bed mounting ears matching P-51 firewall truss
    for (angle =) {
        rotate([0, 0, angle])
        translate([stator_outer_d / 2 + jacket_thickness - 5, -22, 40])
        difference() {
            cube([55, 44, total_core_len - 80]);
            translate([35, 22, -1])
                cylinder(d = 20, h = total_core_len);
        }
    }
}

// --- Full Assembly ---
union() {
    // 4 Coaxial Sawtooth Stacks
    for (s = [0 : stack_count - 1]) {
        translate([0, 0, s * (stack_length + stack_gap)])
            motor_stack_module();
    }

    // Continuous Hollow Propeller Shaft
    color("Silver")
    translate([0, 0, -40])
    difference() {
        cylinder(d = shaft_d, h = total_core_len + thrust_collar_len + 120);
        translate([0, 0, -1])
            cylinder(d = shaft_bore_d, h = total_core_len + thrust_collar_len + 122);
    }

    // Forward Thrust Bearing Housing
    translate([0, 0, total_core_len])
        thrust_bearing_nose();

    // Structural Mounting Lugs
    mounting_lugs();
}
