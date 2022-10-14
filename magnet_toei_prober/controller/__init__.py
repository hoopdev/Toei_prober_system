from typing import NamedTuple
import nidaqmx
import dataclasses
import numpy as np
import datetime


class MagnetOutput(NamedTuple):
    timestamp: datetime.datetime
    field: float
    voltage: float


class MeasuredMagneticField(NamedTuple):
    timestamp: datetime.datetime
    field: float
    hall_voltage: float


@dataclasses.dataclass
class Controller:
    DAQ_ADDRESS: str = "Dev1"
    V_HALL_ADDRESS: str = "ai0"
    V_OUT_ADDRESS: str = "ao0"

    READ_SAMPLE_CLOCK: int = 1000
    READ_SAMPLE_NUM: int = 100

    TIME_VOLTAGE_SWEEP: float = 10e-3
    WRITE_SAMPLE_CLOCK: int = 100e3
    WRITE_ARRAY_LENGTH: int = int(WRITE_SAMPLE_CLOCK * TIME_VOLTAGE_SWEEP)

    V_OUT_MAX: float = 10.0
    V_OUT_MIN: float = -10.0
    V_IN_MAX: float = 10.0
    V_IN_MIN: float = -10.0
    V_UNIT = nidaqmx.constants.VoltageUnits.VOLTS
    V_IN_TERM_CONF = nidaqmx.constants.TerminalConfiguration.RSE

    LOG_PATH: str = "./magnet_controller.log"
    print_log: bool = True
    save_log: bool = True

    _log: dict = dataclasses.field(default_factory=dict, init=False)
    _output_field: MagnetOutput = dataclasses.field(default=None, init=False)
    _measured_field: MeasuredMagneticField = dataclasses.field(default=None, init=False)

    def __post_init__(self) -> None:
        current_field = self.measured_field
        if np.abs(current_field.field) < 10:  # Check the field at first
            self.log("--- Initializing. Magnetic field is zero. ---")
            self._output_field = MagnetOutput(datetime.datetime.now(), 0, 0)
        else:
            self.log("Initial magnetic field is not zero.")
            raise ValueError("Initial magnetic field is not zero.")

    @property
    def measured_field(self) -> MeasuredMagneticField:
        '''Return measured magnetic field using hall sensor'''
        task = nidaqmx.Task()
        task.ai_channels.add_ai_voltage_chan(f"{self.DAQ_ADDRESS}/{self.V_HALL_ADDRESS}", min_val=self.V_IN_MIN, max_val=self.V_IN_MAX, terminal_config=self.V_IN_TERM_CONF, units=self.V_UNIT)
        task.timing.cfg_samp_clk_timing(self.READ_SAMPLE_CLOCK)
        data = task.read(number_of_samples_per_channel=self.READ_SAMPLE_NUM)
        task.wait_until_done()
        task.stop()
        task.close()
        V = np.mean(data)
        H = self.V2H(V)
        self._measured_field = MeasuredMagneticField(datetime.datetime.now(), H, V)
        return self._measured_field

    @property
    def output_field(self) -> MagnetOutput:
        '''Get magnetic field output'''
        return self._output_field

    @output_field.setter
    def output_field(self, target_field: float) -> None:
        '''Set magnetic field output'''
        target_voltage = self.H2V(target_field)
        if (target_voltage < self.V_OUT_MAX) and (target_voltage < self.V_IN_MAX):
            task = nidaqmx.Task()
            task.ao_channels.add_ao_voltage_chan(f'{self.DAQ_ADDRESS}/{self.V_OUT_ADDRESS}', min_val=self.V_OUT_MIN, max_val=self.V_OUT_MAX)
            task.timing.cfg_samp_clk_timing(self.WRITE_SAMPLE_CLOCK)
            v_out = np.linspace(self.output_field.voltage, target_voltage, self.WRITE_ARRAY_LENGTH)
            task.write(v_out, auto_start=True)
            task.wait_until_done()
            task.stop()
            task.close()
            self._output_field = MagnetOutput(datetime.datetime.now(), target_field, target_voltage)
            self.log(f"--- Magnetic field is set to {target_field} Oe. ---")
        else:
            self.log(f"--- Output voltage is not valid. ---")
            raise ValueError("Output voltage is not valid.")
        return

    def H2V(self, H: float) -> float:
        ''' Convert target magnetic field to output voltage
        input: magnetic field (Oe)
        output: voltage (V) 
        '''
        V = -0.01268 + 0.00281 * H + 3.02608e-10 * H**2 - 1.5036e-11 * H**3 - 1.66895e-16 * H**4 + 3.15376e-18 * H**5
        return V

    def V2H(self, V: float) -> float:
        ''' Convert hall voltage to magnetic field
        input: hall voltage (V)
        output: magnetic field (Oe)
        '''
        H = -0.05665 + 260.16273 * V - 2.1979e-5 * V**2 + 0.01858 * V**3 + 1.97225e-4 * V**4 - 2.33726e-4 * V**5
        return H

    def log(self, message) -> None:
        self._log[datetime.datetime.now()] = message
        log_message = f"{datetime.datetime.now()}   {message}"
        if self.print_log:
            print(log_message)
        if self.save_log:
            try:
                with open(self.LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(log_message + "\n")
            except FileNotFoundError:
                with open(self.LOG_PATH, "w", encoding="utf-8") as f:
                    f.write(log_message + "\n")
        return
