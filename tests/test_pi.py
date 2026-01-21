# pylint: disable=line-too-long
""" Tests de PI algorithm used for auto-regulation """

from custom_components.versatile_thermostat.pi_algorithm import PITemperatureRegulator


def test_pi_algorithm_basics():
    """Test the PI algorithm"""

    the_algo = PITemperatureRegulator(
        target_temp=20,
        kp=0.2,
        ki=0.05,
        k_ext=0.1,
        offset_max=2,
        accumulated_error_threshold=20,
        overheat_protection=True,
    )

    assert the_algo

    assert the_algo.calculate_regulated_temperature(20, 20, 1.0) == 20

    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21

    # to reset the accumulated erro
    the_algo.set_target_temp(20)
    the_algo.reset_accumulated_error()

    # Test the accumulator threshold effect and offset_max
    assert the_algo.calculate_regulated_temperature(10, 10, 1.0) == 22  # +2
    assert the_algo.calculate_regulated_temperature(10, 10, 1.0) == 22
    assert the_algo.calculate_regulated_temperature(10, 10, 1.0) == 22
    # Will keep infinitly 22.0

    # to reset the accumulated error
    the_algo.reset_accumulated_error()
    assert the_algo.calculate_regulated_temperature(18, 10, 1.0) == 21.3  # +1.5
    assert the_algo.calculate_regulated_temperature(18.1, 10, 1.0) == 21.4  # +1.6
    assert the_algo.calculate_regulated_temperature(18.3, 10, 1.0) == 21.4  # +1.6
    assert the_algo.calculate_regulated_temperature(18.5, 10, 1.0) == 21.5  # +1.7
    assert the_algo.calculate_regulated_temperature(18.7, 10, 1.0) == 21.6  # +1.7
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 21.6
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21.5  # +1.5
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.1  # error change sign
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 20.9
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21.0

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 12, 1.0) == 20.8
    assert the_algo.calculate_regulated_temperature(20, 15, 1.0) == 20.5
    assert the_algo.calculate_regulated_temperature(20, 18, 1.0) == 20.2  # +0.2
    assert the_algo.calculate_regulated_temperature(20, 20, 1.0) == 20  # =


def test_pi_algorithm_light():
    """Test the PI algorithm"""

    the_algo = PITemperatureRegulator(
        target_temp=20,
        kp=0.2,
        ki=0.05,
        k_ext=0.1,
        offset_max=2,
        accumulated_error_threshold=20,
        overheat_protection=True,
    )

    assert the_algo

    # to reset the accumulated erro
    the_algo.set_target_temp(20)

    assert the_algo.calculate_regulated_temperature(18, 10, 1.0) == 21.3  # +1.5
    assert the_algo.calculate_regulated_temperature(18.1, 10, 1.0) == 21.4  # +1.6
    assert the_algo.calculate_regulated_temperature(18.3, 10, 1.0) == 21.4  # +1.6
    assert the_algo.calculate_regulated_temperature(18.5, 10, 1.0) == 21.5  # +1.7
    assert the_algo.calculate_regulated_temperature(18.7, 10, 1.0) == 21.6  # +1.7
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 21.6  # +1.7
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21.5  # +1.5
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.1  # Error sign change
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 20.9
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 12, 1.0) == 20.8  # +0.8
    assert the_algo.calculate_regulated_temperature(20, 15, 1.0) == 20.5  # +0.5
    assert the_algo.calculate_regulated_temperature(20, 18, 1.0) == 20.2  # +0.2
    assert the_algo.calculate_regulated_temperature(20, 20, 1.0) == 20.0  # =


def test_pi_algorithm_medium():
    """Test the PI algorithm"""

    the_algo = PITemperatureRegulator(
        target_temp=20,
        kp=0.5,
        ki=0.1,
        k_ext=0.1,
        offset_max=3,
        accumulated_error_threshold=30,
        overheat_protection=True,
    )

    assert the_algo

    # to reset the accumulated erro
    the_algo.set_target_temp(20)

    assert the_algo.calculate_regulated_temperature(18, 10, 1.0) == 22.0
    assert the_algo.calculate_regulated_temperature(18.1, 10, 1.0) == 22.1
    assert the_algo.calculate_regulated_temperature(18.3, 10, 1.0) == 22.2
    assert the_algo.calculate_regulated_temperature(18.5, 10, 1.0) == 22.3
    assert the_algo.calculate_regulated_temperature(18.7, 10, 1.0) == 22.4
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 22.3
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21.9
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.0  # error sign change
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 20.7
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 21.1

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 8, 1.0) == 21.3
    assert the_algo.calculate_regulated_temperature(20, 6, 1.0) == 21.5
    assert the_algo.calculate_regulated_temperature(20, 4, 1.0) == 21.7
    assert the_algo.calculate_regulated_temperature(20, 2, 1.0) == 21.9
    assert the_algo.calculate_regulated_temperature(20, 0, 1.0) == 22.1
    assert the_algo.calculate_regulated_temperature(20, -2, 1.0) == 22.3
    assert the_algo.calculate_regulated_temperature(20, -4, 1.0) == 22.5
    assert the_algo.calculate_regulated_temperature(20, -6, 1.0) == 22.7
    assert the_algo.calculate_regulated_temperature(20, -8, 1.0) == 22.9

    # to reset the accumulated erro
    the_algo.set_target_temp(20)
    the_algo.reset_accumulated_error()
    # Test the error acculation effect
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.0
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.1
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.2
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.3
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.4
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.5
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.6
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.7
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.8
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 22.9
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 23
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 23
    assert the_algo.calculate_regulated_temperature(19, 5, 1.0) == 23


def test_pi_algorithm_strong():
    """Test the PI algorithm"""

    the_algo = PITemperatureRegulator(
        target_temp=20,
        kp=0.6,
        ki=0.2,
        k_ext=0.2,
        offset_max=4,
        accumulated_error_threshold=40,
        overheat_protection=True,
    )

    assert the_algo

    # to reset the accumulated erro
    the_algo.set_target_temp(20)

    assert the_algo.calculate_regulated_temperature(18, 10, 1.0) == 23.2
    assert the_algo.calculate_regulated_temperature(18.1, 10, 1.0) == 23.5
    assert the_algo.calculate_regulated_temperature(18.3, 10, 1.0) == 23.8
    assert the_algo.calculate_regulated_temperature(18.5, 10, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(18.7, 10, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 23.9
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 22.3  # error sign change
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.8
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.5
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.3
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 21.1
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 20.9
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 20.7

    # Test temperature external
    assert the_algo.calculate_regulated_temperature(20, 8, 1.0) == 21.5
    assert the_algo.calculate_regulated_temperature(20, 6, 1.0) == 21.9
    assert the_algo.calculate_regulated_temperature(20, 4, 1.0) == 22.3
    assert the_algo.calculate_regulated_temperature(20, 2, 1.0) == 22.7
    assert the_algo.calculate_regulated_temperature(20, 0, 1.0) == 23.1
    assert the_algo.calculate_regulated_temperature(20, -2, 1.0) == 23.5
    assert the_algo.calculate_regulated_temperature(20, -4, 1.0) == 23.9
    assert the_algo.calculate_regulated_temperature(20, -6, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(20, -8, 1.0) == 24

    # to reset the accumulated erro
    the_algo.set_target_temp(20)
    the_algo.reset_accumulated_error()
    # Test the error acculation effect
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 22.6
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 22.8
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 23.0
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 23.2
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 23.4
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 23.6
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 23.8
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 24.0
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 24.0
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 24.0
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 24.0


def test_pi_algorithm_expert():
    """Test the PI algorithm"""

    the_algo = PITemperatureRegulator(
        target_temp=20,
        kp=0.6,
        ki=0.2,
        k_ext=0.2,
        offset_max=4,
        accumulated_error_threshold=40,
        overheat_protection=False,
    )

    assert the_algo
    the_algo.set_target_temp(20)
    assert the_algo.calculate_regulated_temperature(18, 10, 1.0) == 23.2
    assert the_algo.calculate_regulated_temperature(18.1, 10, 1.0) == 23.5
    assert the_algo.calculate_regulated_temperature(18.3, 10, 1.0) == 23.8
    assert the_algo.calculate_regulated_temperature(18.5, 10, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(18.7, 10, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 24
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 23.9
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 23.3
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 23.1
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 22.9
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 23.3
    assert the_algo.calculate_regulated_temperature(19, 10, 1.0) == 23.9
    assert the_algo.calculate_regulated_temperature(22, 10, 1.0) == 22.3


def test_pi_algorithm_time_delta():
    """Test the PI algorithm with time delta"""

    the_algo = PITemperatureRegulator(
        target_temp=20,
        kp=0.6,
        ki=0.2,
        k_ext=0.2,
        offset_max=4,
        accumulated_error_threshold=40,
        overheat_protection=True,
    )

    assert the_algo

    the_algo.set_target_temp(20)
    assert the_algo.calculate_regulated_temperature(18, 10, 1.0) == 23.2
    assert the_algo.calculate_regulated_temperature(18.1, 10, 0.5) == 23.3
    assert the_algo.calculate_regulated_temperature(18.3, 10, 0.8) == 23.5
    assert the_algo.calculate_regulated_temperature(18.5, 10, 1.0) == 23.8

    the_algo.set_target_temp(24)
    assert the_algo.calculate_regulated_temperature(18.7, 10, 0.0) == 28  # Reach the max offset
    assert the_algo.calculate_regulated_temperature(19.1, 10, 0.2) == 28
    assert the_algo.calculate_regulated_temperature(20, 10, 1.0) == 28
    assert the_algo.calculate_regulated_temperature(21, 10, 1.0) == 28
    assert the_algo.calculate_regulated_temperature(22, 10, 1.0) == 28
    assert the_algo.calculate_regulated_temperature(23, 15, 1.0) == 28
    assert the_algo.calculate_regulated_temperature(24, 15, 1.0) == 28
    assert the_algo.calculate_regulated_temperature(25, 15, 1.0) == 26.9  # Overheat protection (sign change)
    assert the_algo.calculate_regulated_temperature(25.8, 18, 0.5) == 25.8
    assert the_algo.calculate_regulated_temperature(25.8, 18, 0.5) == 25.6
    assert the_algo.calculate_regulated_temperature(25, 15, 1.0) == 25.8
    assert the_algo.calculate_regulated_temperature(25, 15, 1.0) == 25.4
    assert the_algo.calculate_regulated_temperature(25, 15, 10.0) == 25.2  # miss 9 cycles, capped
