# pylint: disable=line-too-long
""" Tests de PI algorithm used for auto-regulation """

from custom_components.versatile_thermostat.pi_algorithm import PITemperatureRegulator

def test_pi_algorithm_basics():
    """ Test the PI algorithm """

    the_algo = PITemperatureRegulator(target_temp=20, kp=0.2, ki=0.05, k_ext=0.1, offset_max=2, stabilization_threshold=0.1, accumulated_error_threshold=20)

    assert the_algo

    assert the_algo.calculate_regulated_temperature(20, 20) == 20

    assert the_algo.calculate_regulated_temperature(20, 10) == 21

    # to reset the accumulated erro
    the_algo.set_target_temp(20)
    the_algo.reset_accumulated_error()

    # Test the accumulator threshold effect and offset_max
    assert the_algo.calculate_regulated_temperature(10, 10) == 22   # +2
    assert the_algo.calculate_regulated_temperature(10, 10) == 22
    assert the_algo.calculate_regulated_temperature(10, 10) == 22
    # Will keep infinitly 22.0

    # to reset the accumulated error
    the_algo.reset_accumulated_error()
    assert the_algo.calculate_regulated_temperature(18, 10) == 21.5    # +1.5
    assert the_algo.calculate_regulated_temperature(18.1, 10) == 21.6  # +1.6
    assert the_algo.calculate_regulated_temperature(18.3, 10) == 21.6  # +1.6
    assert the_algo.calculate_regulated_temperature(18.5, 10) == 21.7  # +1.7
    assert the_algo.calculate_regulated_temperature(18.7, 10) == 21.7  # +1.7
    assert the_algo.calculate_regulated_temperature(19, 10) == 21.7    # +1.7
    assert the_algo.calculate_regulated_temperature(20, 10) == 21.5    # +1.5
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.8    # +0.8
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.7    # +0.7
    assert the_algo.calculate_regulated_temperature(20, 10) == 20.9    # +0.7

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 12) == 20.8    # +0.8
    assert the_algo.calculate_regulated_temperature(20, 15) == 20.5    # +0.5
    assert the_algo.calculate_regulated_temperature(20, 18) == 20.2    # +0.2
    assert the_algo.calculate_regulated_temperature(20, 20) == 20.0    # =


def test_pi_algorithm_light():
    """ Test the PI algorithm """

    the_algo = PITemperatureRegulator(target_temp=20, kp=0.2, ki=0.05, k_ext=0.1, offset_max=2, stabilization_threshold=0.1, accumulated_error_threshold=20)

    assert the_algo

    # to reset the accumulated erro
    the_algo.set_target_temp(20)

    assert the_algo.calculate_regulated_temperature(18, 10) == 21.5    # +1.5
    assert the_algo.calculate_regulated_temperature(18.1, 10) == 21.6  # +1.6
    assert the_algo.calculate_regulated_temperature(18.3, 10) == 21.6  # +1.6
    assert the_algo.calculate_regulated_temperature(18.5, 10) == 21.7  # +1.7
    assert the_algo.calculate_regulated_temperature(18.7, 10) == 21.7  # +1.7
    assert the_algo.calculate_regulated_temperature(19, 10) == 21.7    # +1.7
    assert the_algo.calculate_regulated_temperature(20, 10) == 21.5    # +1.5
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.8    # +0.8
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.7    # +0.7
    assert the_algo.calculate_regulated_temperature(20, 10) == 20.9    # +0.7

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 12) == 20.8    # +0.8
    assert the_algo.calculate_regulated_temperature(20, 15) == 20.5    # +0.5
    assert the_algo.calculate_regulated_temperature(20, 18) == 20.2    # +0.2
    assert the_algo.calculate_regulated_temperature(20, 20) == 20.0    # =

def test_pi_algorithm_medium():
    """ Test the PI algorithm """

    the_algo = PITemperatureRegulator(target_temp=20, kp=0.5, ki=0.1, k_ext=0.1, offset_max=3, stabilization_threshold=0.1, accumulated_error_threshold=30)

    assert the_algo

    # to reset the accumulated erro
    the_algo.set_target_temp(20)

    assert the_algo.calculate_regulated_temperature(18, 10) == 22.2
    assert the_algo.calculate_regulated_temperature(18.1, 10) == 22.3
    assert the_algo.calculate_regulated_temperature(18.3, 10) == 22.4
    assert the_algo.calculate_regulated_temperature(18.5, 10) == 22.5
    assert the_algo.calculate_regulated_temperature(18.7, 10) == 22.5
    assert the_algo.calculate_regulated_temperature(19, 10) == 22.4
    assert the_algo.calculate_regulated_temperature(20, 10) == 21.9
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.4
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.3
    assert the_algo.calculate_regulated_temperature(20, 10) == 20.8

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 8) == 21.2
    assert the_algo.calculate_regulated_temperature(20, 6) == 21.4
    assert the_algo.calculate_regulated_temperature(20, 4) == 21.6
    assert the_algo.calculate_regulated_temperature(20, 2) == 21.8
    assert the_algo.calculate_regulated_temperature(20, 0) == 22.0
    assert the_algo.calculate_regulated_temperature(20, -2) == 22.2
    assert the_algo.calculate_regulated_temperature(20, -4) == 22.4
    assert the_algo.calculate_regulated_temperature(20, -6) == 22.6
    assert the_algo.calculate_regulated_temperature(20, -8) == 22.8

    # to reset the accumulated erro
    the_algo.set_target_temp(20)
    the_algo.reset_accumulated_error()
    # Test the error acculation effect
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.1
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.2
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.3
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.4
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.5
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.6
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.7
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.8
    assert the_algo.calculate_regulated_temperature(19, 5) == 22.9
    assert the_algo.calculate_regulated_temperature(19, 5) == 23
    assert the_algo.calculate_regulated_temperature(19, 5) == 23
    assert the_algo.calculate_regulated_temperature(19, 5) == 23
    assert the_algo.calculate_regulated_temperature(19, 5) == 23

def test_pi_algorithm_strong():
    """ Test the PI algorithm """

    the_algo = PITemperatureRegulator(target_temp=20, kp=0.6, ki=0.2, k_ext=0.2, offset_max=4, stabilization_threshold=0.1, accumulated_error_threshold=40)

    assert the_algo

    # to reset the accumulated erro
    the_algo.set_target_temp(20)

    assert the_algo.calculate_regulated_temperature(18, 10) == 23.6
    assert the_algo.calculate_regulated_temperature(18.1, 10) == 23.9
    assert the_algo.calculate_regulated_temperature(18.3, 10) == 24.0
    assert the_algo.calculate_regulated_temperature(18.5, 10) == 24
    assert the_algo.calculate_regulated_temperature(18.7, 10) == 24
    assert the_algo.calculate_regulated_temperature(19, 10) == 24
    assert the_algo.calculate_regulated_temperature(20, 10) == 23.9
    assert the_algo.calculate_regulated_temperature(21, 10) == 21.2
    assert the_algo.calculate_regulated_temperature(21, 10) == 21
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.8
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.6
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.4
    assert the_algo.calculate_regulated_temperature(21, 10) == 20.2
    assert the_algo.calculate_regulated_temperature(21, 10) == 20

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 8) == 21.0
    assert the_algo.calculate_regulated_temperature(20, 6) == 22.8
    assert the_algo.calculate_regulated_temperature(20, 4) == 23.2
    assert the_algo.calculate_regulated_temperature(20, 2) == 23.6
    assert the_algo.calculate_regulated_temperature(20, 0) == 24
    assert the_algo.calculate_regulated_temperature(20, -2) == 24
    assert the_algo.calculate_regulated_temperature(20, -4) == 24
    assert the_algo.calculate_regulated_temperature(20, -6) == 24
    assert the_algo.calculate_regulated_temperature(20, -8) == 24

    # to reset the accumulated erro
    the_algo.set_target_temp(20)
    the_algo.reset_accumulated_error()
    # Test the error acculation effect
    assert the_algo.calculate_regulated_temperature(19, 10) == 22.8
    assert the_algo.calculate_regulated_temperature(19, 10) == 23
    assert the_algo.calculate_regulated_temperature(19, 10) == 23.2
    assert the_algo.calculate_regulated_temperature(19, 10) == 23.4
    assert the_algo.calculate_regulated_temperature(19, 10) == 23.6
    assert the_algo.calculate_regulated_temperature(19, 10) == 23.8
    assert the_algo.calculate_regulated_temperature(19, 10) == 24
    assert the_algo.calculate_regulated_temperature(19, 10) == 24
    assert the_algo.calculate_regulated_temperature(19, 10) == 24
    assert the_algo.calculate_regulated_temperature(19, 10) == 24
    assert the_algo.calculate_regulated_temperature(19, 10) == 24
