###
# Copyright (c) 2016, Johannes Löthberg
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import json
from datetime import datetime

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Wunderground')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class Wunderground(callbacks.Plugin):
    """Queries wundeground.com for weather forecasts"""
    threaded = True

    conditionsApiBase = 'https://api.wunderground.com/api/{}/conditions/q/'
    geonamesApiBase = 'http://api.geonames.org/searchJSON?q={query}&featureClass=P&username={username}'

    def weather(self, irc, msg, args, location):
        """[<location>]"""
        key = self.registryValue('key')
        defaultLocation = self.userValue('defaultLocation', msg.prefix)

        if not location and not defaultLocation:
            irc.error('No location given and no default location set')
            return

        if not location:
            location = defaultLocation

        location = self.lookup_location(location)
        if not location:
            irc.error('Does that place even exist?')
            return


        query = '{},{}'.format(location['lat'], location['lng'])
        (condition, error) = self.get_current_observation(key, query)
        if error:
            irc.error('wunderground: {}'.format(error['description']))
        else:
            irc.reply(u' | '.join(self.format_current_observation(location, condition)))

    weather = wrap(weather, [optional('text')])


    def getdefault(self, irc, msg, args):
        """

        Get the default weather location."""

        location = self.userValue('defaultLocation', msg.prefix)
        if location:
            irc.reply('Default location is "{}"'.format(location))
        else:
            irc.reply('No default location set')

    getdefault = wrap(getdefault)


    def setdefault(self, irc, msg, args, location):
        """<location>

        Set the default weather location."""

        self.setUserValue('defaultLocation', msg.prefix,
                          location, ignoreNoUser=True)
        irc.reply('Default location set to "{}"'.format(location))

    setdefault = wrap(setdefault, ['text'])


    def lookup_location(self, location):
        username = self.registryValue('geonamesUsername')
        url = self.geonamesApiBase.format(**{
            'query': utils.web.urlquote(location),
            'username': utils.web.urlquote(username),
        })
        data = utils.web.getUrl(url)
        data = json.loads(data.decode('utf-8'))
        if data['totalResultsCount'] == 0:
            return {}
        else:
            return data['geonames'][0]


    def get_current_observation(self, key, query):
        url = self.conditionsApiBase.format(utils.web.urlquote(key))
        url += query + '.json'

        data = utils.web.getUrl(url)
        data = json.loads(data.decode('utf-8'))

        if 'current_observation' in data:
            observation = data['current_observation']
            return (observation, None)

        if 'results' in data['response']:
            query = '{}.json'.format(data['response']['results'][0]['l'])
            return self.get_current_observation(key, query)

        return (None, data['response']['error'])


    def format_current_observation(self, location, observation):
        output = []

        location = u'Current weather for {}, {} ({})'.format(
                location['name'],
                location['countryName'],
                observation['station_id'],
        )
        output.append(location)

        temp = u'Temperature: {} °C (Feels like: {} °C)'.format(
                observation.get('temp_c', 'N/A'),
                observation.get('feelslike_c', 'N/A')
        )
        if observation['heat_index_c'] != 'NA':
            temp += u' (Heat Index: {} °C)'.format(observation['heat_index_c'])
        if observation['windchill_c'] != 'NA':
            temp += u' (Wind Chill: {} °C)'.format(observation['windchill_c'])
        output.append(temp)

        humidity = u'Humidity: {}'.format(
            observation.get('relative_humidity', 'N/A%')
        )
        output.append(humidity)

        pressure_mb = float(observation.get('pressure_mb', 0))
        if pressure_mb:
            pressure = u'Pressure: {} kPa'.format(
                    round(pressure_mb / 10, 1)
            )
            output.append(pressure)

        conditions = u'Conditions: {}'.format(
                observation.get('weather', 'N/A')
        )
        output.append(conditions)

        wind_kph = observation.get('wind_kph', None)
        if wind_kph:
            windspeed = round(int(wind_kph) * 1000 / 3600, 2)

        wind = u'Wind: {} at {}'.format(
                observation.get('wind_dir', 'N/A'),
                '{} m/s'.format(windspeed) or 'N/A',
        )
        output.append(wind)

        observation_epoch = int(observation['observation_epoch'])
        updatedDiff = (datetime.now() - datetime.fromtimestamp(observation_epoch)).seconds
        if updatedDiff < 60:
            updated = 'Updated: {} secs ago'.format(updatedDiff)
        else:
            updated = 'Updated: {} mins, {} secs ago'.format(
                    (updatedDiff - (updatedDiff % 60)) // 60,
                    updatedDiff % 60
            )
        output.append(updated)

        return output


Class = Wunderground


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
