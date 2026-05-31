import { Controller, Get } from '@nestjs/common';

@Controller()
export class HealthController {
  constructor() {}

  @Get('health')
  async health() {
    return { status: 'ok', service: 'nestjs-api' };
  }

  @Get('ready')
  async ready() {
    return { ready: true };
  }
}
